from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.storage import S3Storage
from app.models.enums import ArtifactType, RunStatus
from app.models.run import Run
from app.models.run_event import RunEvent
from app.modules.artifacts.service import build_render_object_key, create_artifact
from app.modules.processing.rendering import render_source_model


def start_run_processing(db: Session, *, run: Run, storage: S3Storage) -> Run:
    if run.source_artifact_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload a source model before starting processing.",
        )

    if run.status == RunStatus.RENDERING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Processing is already in progress for this run.",
        )

    if any(artifact.type == ArtifactType.RENDER for artifact in run.artifacts):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Render images have already been generated for this run.",
        )

    source_artifact = next(
        (
            artifact
            for artifact in run.artifacts
            if artifact.id == run.source_artifact_id and artifact.type == ArtifactType.SOURCE_OBJ
        ),
        None,
    )
    if source_artifact is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source artifact metadata is missing for this run.",
        )

    source_bytes = storage.download_bytes(source_artifact.object_key)
    run.status = RunStatus.RENDERING
    db.add(
        RunEvent(
            run_id=run.id,
            event_type="render_started",
            payload_json={"source_artifact_id": run.source_artifact_id},
        )
    )
    db.add(run)
    db.commit()

    try:
        rendered_images = render_source_model(
            source_file_name=source_artifact.file_name,
            source_bytes=source_bytes,
        )

        uploaded_artifact_ids: list[int] = []
        for rendered_image in rendered_images:
            image_bytes = rendered_image.content
            object_key = build_render_object_key(
                user_id=run.user_id,
                run_id=run.id,
                file_name=rendered_image.file_name,
            )
            checksum = sha256(image_bytes).hexdigest()
            storage.upload_bytes(
                data=image_bytes,
                object_key=object_key,
                content_type="image/png",
            )
            artifact = create_artifact(
                artifact_type=ArtifactType.RENDER,
                bucket=storage.bucket,
                user_id=run.user_id,
                run_id=run.id,
                file_name=rendered_image.file_name,
                content_type="image/png",
                object_key=object_key,
                size_bytes=len(image_bytes),
                checksum=checksum,
                meta_json={"render_index": rendered_image.render_index, "source": "blender"},
            )
            db.add(artifact)
            db.flush()
            uploaded_artifact_ids.append(artifact.id)
    except Exception as exc:
        run.status = RunStatus.FAILED
        db.add(
            RunEvent(
                run_id=run.id,
                event_type="render_failed",
                payload_json={"error": str(exc)},
            )
        )
        db.add(run)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Render processing failed.",
        ) from exc

    run.status = RunStatus.RENDERED
    db.add(
        RunEvent(
            run_id=run.id,
            event_type="render_finished",
            payload_json={
                "artifact_ids": uploaded_artifact_ids,
                "render_count": len(uploaded_artifact_ids),
            },
        )
    )
    db.add(run)
    db.commit()
    return run
