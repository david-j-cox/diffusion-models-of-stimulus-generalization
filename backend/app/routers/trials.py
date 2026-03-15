"""Trial data submission endpoints.

Trials are submitted in batches for durable sync. The client buffers
completed trials and posts them periodically or on phase boundaries.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ConditionAssignment, Participant, Trial, TrialEvent
from app.schemas import TrialBatchPayload, TrialBatchResponse
from app.services.study_loader import config_hash

router = APIRouter(prefix="/trials", tags=["trials"])


def _parse_ts(ts_str: str) -> datetime:
    """Parse ISO-8601 timestamp string."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


@router.post("/batch", response_model=TrialBatchResponse)
async def submit_trial_batch(
    payload: TrialBatchPayload, db: AsyncSession = Depends(get_db)
) -> TrialBatchResponse:
    """Submit a batch of completed trials.

    Idempotent: if a trial with the same participant_id + trial_index_global
    already exists, it is skipped (safe for retry on network failure).
    """
    participant = await db.get(Participant, payload.participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    cond = await db.execute(
        select(ConditionAssignment).where(
            ConditionAssignment.participant_id == participant.id
        )
    )
    condition = cond.scalar_one_or_none()
    if not condition:
        raise HTTPException(status_code=400, detail="No condition assignment found")

    # Get existing trial indices for idempotency
    existing_q = select(Trial.trial_index_global).where(
        Trial.participant_id == participant.id
    )
    existing_result = await db.execute(existing_q)
    existing_indices = {row[0] for row in existing_result.all()}

    saved_count = 0
    c_hash = ""  # Will be set from participant's study config
    if participant.study_config_id:
        from app.models import StudyConfig
        sc = await db.get(StudyConfig, participant.study_config_id)
        if sc:
            c_hash = sc.config_hash

    for t in payload.trials:
        if t.trial_index_global in existing_indices:
            continue  # Already saved — skip for idempotency

        trial = Trial(
            participant_id=participant.id,
            session_id=payload.session_id,
            study_config_id=participant.study_config_id,
            condition_id=condition.id,
            phase_id=t.phase_id,
            block_index=t.block_index,
            trial_index_global=t.trial_index_global,
            trial_index_within_phase=t.trial_index_within_phase,
            stimulus_x_normalized=t.stimulus_x_normalized,
            stimulus_render_value=t.stimulus_render_value,
            stimulus_label=t.stimulus_label,
            signed_distance_from_target=t.signed_distance_from_target,
            absolute_distance_from_target=t.absolute_distance_from_target,
            similarity_gaussian=t.similarity_gaussian,
            similarity_exponential=t.similarity_exponential,
            trial_type=t.trial_type,
            reinforcement_available=t.reinforcement_available,
            reinforcement_delivered=t.reinforcement_delivered,
            feedback_type=t.feedback_type,
            response_occurred=t.response_occurred,
            response_count=t.response_count,
            first_response_rt_ms=t.first_response_rt_ms,
            all_response_timestamps_ms=t.all_response_timestamps_ms,
            trial_start_ts=_parse_ts(t.trial_start_ts),
            stimulus_onset_ts=_parse_ts(t.stimulus_onset_ts),
            feedback_onset_ts=_parse_ts(t.feedback_onset_ts) if t.feedback_onset_ts else None,
            trial_end_ts=_parse_ts(t.trial_end_ts),
            browser_tz_offset=t.browser_tz_offset,
            client_metadata=t.client_metadata,
            is_resumed=t.is_resumed,
            is_attention_check=t.is_attention_check,
            exclusion_flag=None,
            config_hash=c_hash,
            random_seed=condition.random_seed,
        )
        db.add(trial)
        await db.flush()

        # Save sub-trial events
        for evt in t.events:
            db.add(TrialEvent(
                trial_id=trial.id,
                event_type=evt.event_type,
                key=evt.key,
                timestamp_ms=evt.timestamp_ms,
                relative_to_onset_ms=evt.relative_to_onset_ms,
            ))

        saved_count += 1

    await db.commit()

    # Count total trials for this participant
    total_q = select(func.count()).select_from(Trial).where(
        Trial.participant_id == participant.id
    )
    total = (await db.execute(total_q)).scalar_one()

    return TrialBatchResponse(saved_count=saved_count, next_expected_trial=total)


@router.get("/progress/{participant_id}")
async def get_progress(
    participant_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Get the current trial progress for a participant."""
    import uuid as _uuid
    pid = _uuid.UUID(participant_id)
    count_q = select(func.count()).select_from(Trial).where(Trial.participant_id == pid)
    result = await db.execute(count_q)
    return {"participant_id": participant_id, "trials_completed": result.scalar_one()}
