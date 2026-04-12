from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ArtifactType, RunStatus


class RunCreateRequest(BaseModel):
    name: str | None = None


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ArtifactType
    file_name: str
    content_type: str
    size_bytes: int | None
    checksum: str | None
    download_url: str | None = None
    created_at: datetime


class RunEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    payload_json: dict | None
    created_at: datetime


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str | None
    status: RunStatus
    source_artifact_id: int | None
    selected_collage_artifact_id: int | None
    latest_generation_id: int | None
    created_at: datetime
    updated_at: datetime
    artifacts: list[ArtifactResponse]
    events: list[RunEventResponse]
