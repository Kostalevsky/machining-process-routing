from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.infrastructure.storage import S3Storage, get_storage
from app.models.user import User
from app.modules.collages.service import generate_collages_for_run, select_collage_for_run
from app.modules.generations.service import create_generation_for_run
from app.modules.identity.service import get_current_user
from app.modules.processing.service import start_run_processing
from app.modules.runs.schemas import (
    ArtifactResponse,
    CollageGenerateRequest,
    CollageSelectRequest,
    GenerationCreateRequest,
    RunCreateRequest,
    RunResponse,
)
from app.modules.runs.service import (
    create_run,
    get_run_for_user,
    get_selected_collage_artifact,
    list_runs_for_user,
    serialize_artifact,
    serialize_run,
    upload_render_images,
    upload_source_model,
)

router = APIRouter(prefix="/runs", tags=["runs"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Storage = Annotated[S3Storage, Depends(get_storage)]


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run_endpoint(
    payload: RunCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
) -> RunResponse:
    run = create_run(db, user=current_user, name=payload.name)
    return serialize_run(storage, run)


@router.get("", response_model=list[RunResponse])
def list_runs_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
) -> list[RunResponse]:
    runs = list_runs_for_user(db, user_id=current_user.id)
    return [serialize_run(storage, run) for run in runs]


@router.get("/{run_id}", response_model=RunResponse)
def get_run_endpoint(
    run_id: int,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
) -> RunResponse:
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    return serialize_run(storage, run)


@router.get("/{run_id}/selected-collage", response_model=ArtifactResponse)
def get_selected_collage_endpoint(
    run_id: int,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
) -> ArtifactResponse:
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    artifact = get_selected_collage_artifact(run)
    return serialize_artifact(storage, artifact)


@router.post("/{run_id}/source-file", response_model=RunResponse)
async def upload_source_file_endpoint(
    run_id: int,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
    file: UploadFile = File(...),
) -> RunResponse:
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    run = await upload_source_model(db, run=run, file=file, storage=storage)
    return serialize_run(storage, run)


@router.post("/{run_id}/renders", response_model=RunResponse)
async def upload_renders_endpoint(
    run_id: int,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
    files: list[UploadFile] = File(...),
) -> RunResponse:
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    run = await upload_render_images(db, run=run, files=files, storage=storage)
    return serialize_run(storage, run)


@router.post(
    "/{run_id}/collages/generate",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_collages_endpoint(
    run_id: int,
    payload: CollageGenerateRequest,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
) -> RunResponse:
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    run = generate_collages_for_run(
        db,
        run=run,
        storage=storage,
        counts=payload.counts,
        selected_count=payload.selected_count,
    )
    run = get_run_for_user(db, run_id=run.id, user_id=current_user.id)
    return serialize_run(storage, run)


@router.post("/{run_id}/collages/select", response_model=RunResponse)
def select_collage_endpoint(
    run_id: int,
    payload: CollageSelectRequest,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
) -> RunResponse:
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    run = select_collage_for_run(db, run=run, collage_artifact_id=payload.collage_artifact_id)
    run = get_run_for_user(db, run_id=run.id, user_id=current_user.id)
    return serialize_run(storage, run)


@router.post(
    "/{run_id}/generations",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_generation_endpoint(
    run_id: int,
    payload: GenerationCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
) -> RunResponse:
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    run = create_generation_for_run(
        db,
        run=run,
        storage=storage,
        provider=payload.provider,
        model_name=payload.model_name,
        prompt_version=payload.prompt_version,
    )
    run = get_run_for_user(db, run_id=run.id, user_id=current_user.id)
    return serialize_run(storage, run)


@router.post("/{run_id}/process", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_processing_endpoint(
    run_id: int,
    db: DbSession,
    current_user: CurrentUser,
    storage: Storage,
) -> RunResponse:
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    run = start_run_processing(db, run=run, storage=storage)
    run = get_run_for_user(db, run_id=run.id, user_id=current_user.id)
    return serialize_run(storage, run)
