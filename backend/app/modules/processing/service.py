from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import RunStatus
from app.models.run import Run
from app.models.run_event import RunEvent


def start_run_processing(db: Session, *, run: Run) -> Run:
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
    db.refresh(run)
    return run
