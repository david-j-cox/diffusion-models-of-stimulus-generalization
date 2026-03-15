"""Admin / researcher endpoints for data export and participant management."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Exclusion, Participant
from app.schemas import ExcludeRequest, ParticipantSummary
from app.services.export import export_participant_summary, export_trials_csv

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/participants")
async def list_participants(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List all participants with summary info."""
    return await export_participant_summary(db)


@router.get("/export/trials.csv")
async def download_trials_csv(
    exclude_pilots: bool = False,
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Download all trial data as CSV."""
    csv_data = await export_trials_csv(db, exclude_pilots=exclude_pilots)
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trials.csv"},
    )


@router.post("/exclude")
async def exclude_participant(
    req: ExcludeRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Add an exclusion flag to a participant. Does not delete data."""
    participant = await db.get(Participant, req.participant_id)
    if not participant:
        return {"error": "Participant not found"}

    exc = Exclusion(
        participant_id=req.participant_id,
        reason=req.reason,
        source=req.source,
    )
    db.add(exc)
    await db.commit()
    return {"status": "excluded", "participant_id": str(req.participant_id)}


@router.post("/mark-pilot/{participant_id}")
async def mark_pilot(
    participant_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Mark a participant as a pilot run."""
    import uuid
    p = await db.get(Participant, uuid.UUID(participant_id))
    if not p:
        return {"error": "Participant not found"}
    p.is_pilot = True
    await db.commit()
    return {"status": "marked_pilot", "participant_id": participant_id}
