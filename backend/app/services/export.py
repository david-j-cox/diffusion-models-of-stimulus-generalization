"""Data export utilities for admin and analysis pipeline."""

from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Completion,
    ConditionAssignment,
    Exclusion,
    Participant,
    ScreenEvent,
    Session,
    Trial,
)


TRIAL_CSV_COLUMNS = [
    "participant_id",
    "external_id",
    "session_id",
    "study_config_id",
    "condition_id",
    "condition_name",
    "phase_id",
    "block_index",
    "trial_index_global",
    "trial_index_within_phase",
    "stimulus_x_normalized",
    "stimulus_render_value",
    "stimulus_label",
    "signed_distance_from_target",
    "absolute_distance_from_target",
    "similarity_gaussian",
    "similarity_exponential",
    "trial_type",
    "reinforcement_available",
    "reinforcement_delivered",
    "feedback_type",
    "response_occurred",
    "response_count",
    "first_response_rt_ms",
    "all_response_timestamps_ms",
    "trial_start_ts",
    "stimulus_onset_ts",
    "feedback_onset_ts",
    "trial_end_ts",
    "browser_tz_offset",
    "is_resumed",
    "is_attention_check",
    "exclusion_flag",
    "config_hash",
    "random_seed",
]


async def export_trials_csv(
    db: AsyncSession,
    study_config_id: str | None = None,
    exclude_pilots: bool = False,
) -> str:
    """Export all trial data as CSV string."""
    query = (
        select(Trial, Participant.external_id, ConditionAssignment.condition_name)
        .join(Participant, Trial.participant_id == Participant.id)
        .outerjoin(ConditionAssignment, Trial.condition_id == ConditionAssignment.id)
        .order_by(Trial.participant_id, Trial.trial_index_global)
    )

    if study_config_id:
        query = query.where(Trial.study_config_id == study_config_id)
    if exclude_pilots:
        query = query.where(Participant.is_pilot == False)  # noqa: E712

    result = await db.execute(query)
    rows = result.all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TRIAL_CSV_COLUMNS)
    writer.writeheader()

    for trial, ext_id, cond_name in rows:
        row = {col: getattr(trial, col, None) for col in TRIAL_CSV_COLUMNS}
        row["external_id"] = ext_id
        row["condition_name"] = cond_name
        writer.writerow(row)

    return output.getvalue()


async def export_participant_summary(db: AsyncSession) -> list[dict[str, Any]]:
    """Return a summary list of all participants."""
    query = (
        select(Participant)
        .options(
            selectinload(Participant.condition_assignment),
            selectinload(Participant.completion),
            selectinload(Participant.exclusions),
        )
        .order_by(Participant.created_at)
    )
    result = await db.execute(query)
    participants = result.scalars().all()

    summaries = []
    for p in participants:
        summaries.append({
            "id": str(p.id),
            "external_id": p.external_id,
            "condition_name": p.condition_assignment.condition_name if p.condition_assignment else None,
            "is_pilot": p.is_pilot,
            "completed": p.completion is not None,
            "excluded": len(p.exclusions) > 0,
            "exclusion_reasons": [e.reason for e in p.exclusions],
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        })

    return summaries
