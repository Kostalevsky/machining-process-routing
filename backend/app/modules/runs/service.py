from hashlib import sha256

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.storage import S3Storage
from app.models.artifact import Artifact
from app.models.enums import ArtifactType, RunStatus
from app.models.run import Run
from app.models.run_event import RunEvent
from app.models.user import User
from app.modules.artifacts.service import (
    build_artifact_download_url,
    build_render_object_key,
    build_source_object_key,
    create_artifact,
    validate_render_file,
    validate_source_file,
)
from app.modules.runs.schemas import (
    ArtifactResponse,
    GenerationResponse,
    RunEventResponse,
    RunResponse,
)

RUN_DETAIL_LOAD_OPTIONS = (
    selectinload(Run.artifacts),
    selectinload(Run.events),
    selectinload(Run.generations),
)


def create_run(db: Session, *, user: User, name: str | None) -> Run:
    run = Run(user_id=user.id, name=name, status=RunStatus.CREATED)
    db.add(run)
    db.flush()
    db.add(RunEvent(run_id=run.id, event_type="run_created", payload_json={"name": name}))
    db.commit()
    return get_run_for_user(db, run_id=run.id, user_id=user.id)


def list_runs_for_user(db: Session, *, user_id: int) -> list[Run]:
    statement = (
        select(Run)
        .where(Run.user_id == user_id)
        .options(*RUN_DETAIL_LOAD_OPTIONS)
        .order_by(Run.created_at.desc())
    )
    return list(db.scalars(statement).unique())


def get_run_for_user(db: Session, *, run_id: int, user_id: int) -> Run:
    statement = (
        select(Run)
        .where(Run.id == run_id, Run.user_id == user_id)
        .options(*RUN_DETAIL_LOAD_OPTIONS)
    )
    run = db.scalar(statement)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run


async def upload_source_model(
    db: Session,
    *,
    run: Run,
    file: UploadFile,
    storage: S3Storage,
) -> Run:
    if run.source_artifact_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source model has already been uploaded for this run.",
        )

    file_name = file.filename or "model.obj"
    validate_source_file(file_name)

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    object_key = build_source_object_key(user_id=run.user_id, run_id=run.id, file_name=file_name)
    content_type = file.content_type or "model/obj"
    checksum = sha256(raw_bytes).hexdigest()

    storage.upload_bytes(data=raw_bytes, object_key=object_key, content_type=content_type)

    artifact = create_artifact(
        artifact_type=ArtifactType.SOURCE_OBJ,
        bucket=storage.bucket,
        user_id=run.user_id,
        run_id=run.id,
        file_name=file_name,
        content_type=content_type,
        object_key=object_key,
        size_bytes=len(raw_bytes),
        checksum=checksum,
        meta_json={"upload_kind": "source"},
    )
    db.add(artifact)
    db.flush()

    run.source_artifact_id = artifact.id
    run.status = RunStatus.SOURCE_UPLOADED
    db.add(run)
    db.add(
        RunEvent(
            run_id=run.id,
            event_type="source_uploaded",
            payload_json={"artifact_id": artifact.id, "file_name": file_name},
        )
    )
    db.commit()
    return get_run_for_user(db, run_id=run.id, user_id=run.user_id)


async def upload_render_images(
    db: Session,
    *,
    run: Run,
    files: list[UploadFile],
    storage: S3Storage,
) -> Run:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one render image must be uploaded.",
        )

    uploaded_artifacts: list[Artifact] = []
    for index, file in enumerate(files):
        file_name = file.filename or f"render_{index + 1}.png"
        validate_render_file(file_name)

        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded render image is empty.",
            )

        object_key = build_render_object_key(
            user_id=run.user_id,
            run_id=run.id,
            file_name=file_name,
        )
        content_type = file.content_type or "image/png"
        checksum = sha256(raw_bytes).hexdigest()

        storage.upload_bytes(data=raw_bytes, object_key=object_key, content_type=content_type)
        artifact = create_artifact(
            artifact_type=ArtifactType.RENDER,
            bucket=storage.bucket,
            user_id=run.user_id,
            run_id=run.id,
            file_name=file_name,
            content_type=content_type,
            object_key=object_key,
            size_bytes=len(raw_bytes),
            checksum=checksum,
            meta_json={"render_index": index + 1, "upload_kind": "render"},
        )
        db.add(artifact)
        db.flush()
        uploaded_artifacts.append(artifact)

    run.status = RunStatus.RENDERED
    db.add(run)
    db.add(
        RunEvent(
            run_id=run.id,
            event_type="renders_uploaded",
            payload_json={"artifact_ids": [artifact.id for artifact in uploaded_artifacts]},
        )
    )
    db.commit()
    return get_run_for_user(db, run_id=run.id, user_id=run.user_id)


def serialize_run(storage: S3Storage, run: Run) -> RunResponse:
    artifact_payloads = [
        serialize_artifact(storage, artifact)
        for artifact in sorted(run.artifacts, key=lambda item: item.created_at, reverse=True)
    ]
    event_payloads = [
        RunEventResponse(
            id=event.id,
            event_type=event.event_type,
            payload_json=event.payload_json,
            created_at=event.created_at,
        )
        for event in sorted(run.events, key=lambda item: item.created_at, reverse=True)
    ]
    generation_payloads = [
        GenerationResponse(
            id=generation.id,
            input_collage_artifact_id=generation.input_collage_artifact_id,
            output_artifact_id=generation.output_artifact_id,
            provider=generation.provider,
            model_name=generation.model_name,
            prompt_version=generation.prompt_version,
            status=generation.status,
            error_message=generation.error_message,
            created_at=generation.created_at,
            completed_at=generation.completed_at,
        )
        for generation in sorted(run.generations, key=lambda item: item.created_at, reverse=True)
    ]
    return RunResponse(
        id=run.id,
        user_id=run.user_id,
        name=run.name,
        status=run.status,
        source_artifact_id=run.source_artifact_id,
        selected_collage_artifact_id=run.selected_collage_artifact_id,
        latest_generation_id=run.latest_generation_id,
        created_at=run.created_at,
        updated_at=run.updated_at,
        artifacts=artifact_payloads,
        events=event_payloads,
        generations=generation_payloads,
    )


def get_selected_collage_artifact(run: Run) -> Artifact:
    if run.selected_collage_artifact_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No selected collage for this run.",
        )

    artifact = next(
        (
            item
            for item in run.artifacts
            if item.id == run.selected_collage_artifact_id and item.type == ArtifactType.COLLAGE
        ),
        None,
    )
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected collage artifact was not found for this run.",
        )
    return artifact


def serialize_artifact(storage: S3Storage, artifact: Artifact) -> ArtifactResponse:
    return ArtifactResponse(
        id=artifact.id,
        type=artifact.type,
        file_name=artifact.file_name,
        content_type=artifact.content_type,
        size_bytes=artifact.size_bytes,
        checksum=artifact.checksum,
        meta_json=artifact.meta_json,
        download_url=build_artifact_download_url(storage, artifact),
        created_at=artifact.created_at,
    )
