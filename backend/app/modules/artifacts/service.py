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


def validate_source_file(file_name: str) -> None:
    if not file_name.lower().endswith(".obj"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .obj files are supported for source uploads.",
        )


def create_source_artifact(
    *,
    bucket: str,
    user_id: int,
    run_id: int,
    file_name: str,
    content_type: str,
    object_key: str,
    size_bytes: int,
    checksum: str,
) -> Artifact:
    return Artifact(
        run_id=run_id,
        user_id=user_id,
        type=ArtifactType.SOURCE_OBJ,
        bucket=bucket,
        object_key=object_key,
        file_name=file_name,
        content_type=content_type,
        size_bytes=size_bytes,
        checksum=checksum,
        meta_json={"upload_kind": "source"},
    )
