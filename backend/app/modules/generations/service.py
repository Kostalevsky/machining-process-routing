from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.storage import S3Storage
from app.models.enums import ArtifactType, GenerationStatus, RunStatus
from app.models.generation import Generation
from app.models.run import Run
from app.models.run_event import RunEvent
from app.modules.artifacts.service import build_generated_json_object_key, create_artifact


def create_generation_for_run(
    db: Session,
    *,
    run: Run,
    storage: S3Storage,
    provider: str,
    model_name: str,
    prompt_version: str,
) -> Run:
    if run.selected_collage_artifact_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Select or generate a collage before starting generation.",
        )

    collage_artifact = next(
        (artifact for artifact in run.artifacts if artifact.id == run.selected_collage_artifact_id),
        None,
    )
    if collage_artifact is None or collage_artifact.type != ArtifactType.COLLAGE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected collage artifact is missing or invalid.",
        )

    generation = Generation(
        run_id=run.id,
        user_id=run.user_id,
        input_collage_artifact_id=collage_artifact.id,
        provider=provider,
        model_name=model_name,
        prompt_version=prompt_version,
        status=GenerationStatus.RUNNING,
    )
    db.add(generation)
    db.flush()

    db.add(
        RunEvent(
            run_id=run.id,
            event_type="generation_started",
            payload_json={
                "generation_id": generation.id,
                "collage_artifact_id": collage_artifact.id,
            },
        )
    )

    generated_payload = {
        "run_id": run.id,
        "user_id": run.user_id,
        "generation_id": generation.id,
        "provider": provider,
        "model_name": model_name,
        "prompt_version": prompt_version,
        "input_collage_artifact_id": collage_artifact.id,
        "status": "stub_generated",
        "generated_at": datetime.now(UTC).isoformat(),
    }
    generated_bytes = (
        json.dumps(generated_payload, ensure_ascii=True, indent=2) + "\n"
    ).encode("utf-8")
    object_key = build_generated_json_object_key(user_id=run.user_id, run_id=run.id)
    checksum = sha256(generated_bytes).hexdigest()
    storage.upload_bytes(
        data=generated_bytes,
        object_key=object_key,
        content_type="application/json",
    )
    artifact = create_artifact(
        artifact_type=ArtifactType.GENERATED_JSON,
        bucket=storage.bucket,
        user_id=run.user_id,
        run_id=run.id,
        file_name=f"generation_{generation.id}.json",
        content_type="application/json",
        object_key=object_key,
        size_bytes=len(generated_bytes),
        checksum=checksum,
        meta_json={
            "generation_id": generation.id,
            "provider": provider,
            "model_name": model_name,
            "prompt_version": prompt_version,
        },
    )
    db.add(artifact)
    db.flush()

    generation.output_artifact_id = artifact.id
    generation.status = GenerationStatus.SUCCEEDED
    generation.completed_at = datetime.now(UTC)
    db.add(generation)

    run.latest_generation_id = generation.id
    run.status = RunStatus.COMPLETED
    db.add(run)
    db.add(
        RunEvent(
            run_id=run.id,
            event_type="generation_completed",
            payload_json={"generation_id": generation.id, "artifact_id": artifact.id},
        )
    )
    db.commit()
    db.refresh(run)
    return run
