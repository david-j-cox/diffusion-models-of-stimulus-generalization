"""Participant registration, session resume, and completion endpoints."""

from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Completion, Participant, Session, Trial
from app.schemas import (
    CompleteRequest,
    CompleteResponse,
    ConditionInfo,
    RegisterRequest,
    RegisterResponse,
    ResumeRequest,
    ResumeResponse,
    ScreenEventPayload,
)
from app.services.assignment import assign_condition
from app.services.sequence import generate_full_sequence
from app.services.study_loader import config_hash, ensure_study_config
from app.models import ScreenEvent

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("/register", response_model=RegisterResponse)
async def register_participant(
    req: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    """Register a new participant or return existing registration if external_id matches."""

    # Check if participant already exists (idempotent for page refreshes)
    existing = await db.execute(
        select(Participant).where(Participant.external_id == req.external_id)
    )
    participant = existing.scalar_one_or_none()

    sc, config_dict = await ensure_study_config(db, settings.default_study_config)
    c_hash = config_hash(config_dict)

    if participant:
        # Returning participant — create a resume session
        session = Session(
            participant_id=participant.id,
            user_agent=req.user_agent,
            viewport_width=req.viewport_width,
            viewport_height=req.viewport_height,
            timezone_offset=req.timezone_offset,
            is_resume=True,
        )
        db.add(session)

        # Find how far they got
        trial_count = await db.execute(
            select(func.count()).select_from(Trial).where(
                Trial.participant_id == participant.id
            )
        )
        resume_from = trial_count.scalar_one()

        await db.commit()

        # Get their condition
        cond = participant.condition_assignment
        if not cond:
            raise HTTPException(status_code=500, detail="Participant has no condition assignment")

        return RegisterResponse(
            participant_id=participant.id,
            session_id=session.id,
            condition=ConditionInfo(
                condition_name=cond.condition_name,
                condition_index=cond.condition_index,
                target_x=cond.target_x,
                random_seed=cond.random_seed,
                assignment=cond.assignment_json,
            ),
            study_config=config_dict,
            resume_from_trial=resume_from,
        )

    # New participant
    participant = Participant(
        external_id=req.external_id,
        study_config_id=sc.id,
    )
    db.add(participant)
    await db.flush()

    # Assign condition
    cond = await assign_condition(db, participant, config_dict, c_hash)

    # Create session
    session = Session(
        participant_id=participant.id,
        user_agent=req.user_agent,
        viewport_width=req.viewport_width,
        viewport_height=req.viewport_height,
        timezone_offset=req.timezone_offset,
        is_resume=False,
    )
    db.add(session)
    await db.commit()

    return RegisterResponse(
        participant_id=participant.id,
        session_id=session.id,
        condition=ConditionInfo(
            condition_name=cond.condition_name,
            condition_index=cond.condition_index,
            target_x=cond.target_x,
            random_seed=cond.random_seed,
            assignment=cond.assignment_json,
        ),
        study_config=config_dict,
        resume_from_trial=None,
    )


@router.post("/resume", response_model=ResumeResponse)
async def resume_session(
    req: ResumeRequest, db: AsyncSession = Depends(get_db)
) -> ResumeResponse:
    """Create a new session for a returning participant."""
    participant = await db.get(Participant, req.participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    session = Session(
        participant_id=participant.id,
        user_agent=req.user_agent,
        viewport_width=req.viewport_width,
        viewport_height=req.viewport_height,
        timezone_offset=req.timezone_offset,
        is_resume=True,
    )
    db.add(session)

    trial_count = await db.execute(
        select(func.count()).select_from(Trial).where(
            Trial.participant_id == participant.id
        )
    )
    resume_from = trial_count.scalar_one()

    await db.commit()

    return ResumeResponse(session_id=session.id, resume_from_trial=resume_from)


@router.post("/complete", response_model=CompleteResponse)
async def complete_experiment(
    req: CompleteRequest, db: AsyncSession = Depends(get_db)
) -> CompleteResponse:
    """Generate and return a completion code."""
    participant = await db.get(Participant, req.participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Check for existing completion
    existing = await db.execute(
        select(Completion).where(Completion.participant_id == participant.id)
    )
    comp = existing.scalar_one_or_none()
    if comp:
        return CompleteResponse(completion_code=comp.completion_code)

    # Generate completion code
    code = hashlib.sha256(
        f"{participant.id}:{participant.external_id}".encode()
    ).hexdigest()[:12].upper()

    comp = Completion(
        participant_id=participant.id,
        completion_code=code,
    )
    db.add(comp)

    participant.completed_at = func.now()
    await db.commit()

    return CompleteResponse(completion_code=code)


@router.post("/screen-event")
async def log_screen_event(
    payload: ScreenEventPayload, db: AsyncSession = Depends(get_db)
) -> dict:
    """Log a screen-level event (consent, phase start, etc.)."""
    event = ScreenEvent(
        participant_id=payload.participant_id,
        session_id=payload.session_id,
        event_name=payload.event_name,
        metadata_json=payload.metadata_json,
    )
    db.add(event)
    await db.commit()
    return {"status": "ok"}
