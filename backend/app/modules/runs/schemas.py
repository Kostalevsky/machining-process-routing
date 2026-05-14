from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.models.enums import ArtifactType, GenerationStatus, RunStatus


class RunCreateRequest(BaseModel):
    name: str | None = None


class CollageGenerateRequest(BaseModel):
    counts: list[int] = Field(default_factory=lambda: [3, 4, 6])
    selected_count: int | None = None


class CollageSelectRequest(BaseModel):
    collage_artifact_id: int


class GenerationCreateRequest(BaseModel):
    provider: str = settings.ml_default_provider
    model_name: str = settings.ml_default_model_name
    prompt_version: str = settings.ml_prompt_version


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ArtifactType
    file_name: str
    content_type: str
    size_bytes: int | None
    checksum: str | None
    meta_json: dict | None
    download_url: str | None = None
    created_at: datetime


class RunEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    payload_json: dict | None
    created_at: datetime


class GenerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    input_collage_artifact_id: int | None
    output_artifact_id: int | None
    provider: str | None
    model_name: str | None
    prompt_version: str | None
    status: GenerationStatus
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


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
    generations: list[GenerationResponse]
