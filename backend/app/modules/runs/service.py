from hashlib import sha256

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.storage import S3Storage
from app.models.enums import RunStatus
from app.models.run import Run
from app.models.run_event import RunEvent
from app.models.user import User
from app.modules.artifacts.service import (
    build_artifact_download_url,
    build_source_object_key,
    create_source_artifact,
    validate_source_file,
)
from app.modules.runs.schemas import ArtifactResponse, RunEventResponse, RunResponse


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
        .options(selectinload(Run.artifacts), selectinload(Run.events))
        .order_by(Run.created_at.desc())
    )
    return list(db.scalars(statement).unique())


def get_run_for_user(db: Session, *, run_id: int, user_id: int) -> Run:
    statement = (
        select(Run)
        .where(Run.id == run_id, Run.user_id == user_id)
        .options(selectinload(Run.artifacts), selectinload(Run.events))
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

    artifact = create_source_artifact(
        bucket=storage.bucket,
        user_id=run.user_id,
        run_id=run.id,
        file_name=file_name,
        content_type=content_type,
        object_key=object_key,
        size_bytes=len(raw_bytes),
        checksum=checksum,
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


def serialize_run(storage: S3Storage, run: Run) -> RunResponse:
    artifact_payloads = [
        ArtifactResponse(
            id=artifact.id,
            type=artifact.type,
            file_name=artifact.file_name,
            content_type=artifact.content_type,
            size_bytes=artifact.size_bytes,
            checksum=artifact.checksum,
            download_url=build_artifact_download_url(storage, artifact),
            created_at=artifact.created_at,
        )
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
    )
