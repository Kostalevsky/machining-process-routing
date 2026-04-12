from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.infrastructure.storage import S3Storage
from app.models.user import User
from app.modules.identity.service import get_current_user
from app.modules.processing.service import start_run_processing
from app.modules.runs.schemas import RunCreateRequest, RunResponse
from app.modules.runs.service import (
    create_run,
    get_run_for_user,
    list_runs_for_user,
    serialize_run,
    upload_source_model,
)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run_endpoint(
    payload: RunCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    storage = S3Storage()
    run = create_run(db, user=current_user, name=payload.name)
    return serialize_run(storage, run)


@router.get("", response_model=list[RunResponse])
def list_runs_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RunResponse]:
    storage = S3Storage()
    runs = list_runs_for_user(db, user_id=current_user.id)
    return [serialize_run(storage, run) for run in runs]


@router.get("/{run_id}", response_model=RunResponse)
def get_run_endpoint(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    storage = S3Storage()
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    return serialize_run(storage, run)


@router.post("/{run_id}/source-file", response_model=RunResponse)
async def upload_source_file_endpoint(
    run_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    storage = S3Storage()
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    run = await upload_source_model(db, run=run, file=file, storage=storage)
    return serialize_run(storage, run)


@router.post("/{run_id}/process", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_processing_endpoint(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    storage = S3Storage()
    run = get_run_for_user(db, run_id=run_id, user_id=current_user.id)
    run = start_run_processing(db, run=run)
    run = get_run_for_user(db, run_id=run.id, user_id=current_user.id)
    return serialize_run(storage, run)
