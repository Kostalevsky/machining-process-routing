from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.infrastructure.storage import S3Storage
from app.models.artifact import Artifact
from app.models.enums import ArtifactType


def build_artifact_download_url(storage: S3Storage, artifact: Artifact) -> str:
    return storage.generate_presigned_url(artifact.object_key)


def build_source_object_key(*, user_id: int, run_id: int, file_name: str) -> str:
    safe_name = Path(file_name).name
    return f"users/{user_id}/runs/{run_id}/source/{uuid4().hex}_{safe_name}"


def build_render_object_key(*, user_id: int, run_id: int, file_name: str) -> str:
    safe_name = Path(file_name).name
    return f"users/{user_id}/runs/{run_id}/renders/{uuid4().hex}_{safe_name}"


def build_collage_object_key(*, user_id: int, run_id: int, count: int) -> str:
    return f"users/{user_id}/runs/{run_id}/collages/{count}_{uuid4().hex}.png"


def build_generated_json_object_key(*, user_id: int, run_id: int) -> str:
    return f"users/{user_id}/runs/{run_id}/generated/{uuid4().hex}.json"


def validate_source_file(file_name: str) -> None:
    if not file_name.lower().endswith(".obj"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .obj files are supported for source uploads.",
        )


def validate_render_file(file_name: str) -> None:
    allowed_extensions = {".png", ".jpg", ".jpeg"}
    extension = Path(file_name).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .png, .jpg, and .jpeg files are supported for render uploads.",
        )


def create_artifact(
    *,
    artifact_type: ArtifactType,
    bucket: str,
    user_id: int,
    run_id: int,
    file_name: str,
    content_type: str,
    object_key: str,
    size_bytes: int,
    checksum: str,
    meta_json: dict | None = None,
) -> Artifact:
    return Artifact(
        run_id=run_id,
        user_id=user_id,
        type=artifact_type,
        bucket=bucket,
        object_key=object_key,
        file_name=file_name,
        content_type=content_type,
        size_bytes=size_bytes,
        checksum=checksum,
        meta_json=meta_json,
    )
