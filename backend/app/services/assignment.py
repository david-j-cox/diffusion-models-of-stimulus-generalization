"""Participant condition assignment and counterbalancing.

Deterministic assignment based on participant sequence number so conditions
are balanced. The sequence number is the count of prior participants in the
same study config.
"""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConditionAssignment, Participant


def _deterministic_seed(external_id: str, config_hash: str) -> int:
    """Produce a deterministic integer seed from participant + config identifiers."""
    digest = hashlib.sha256(f"{external_id}:{config_hash}".encode()).hexdigest()
    return int(digest[:8], 16)


async def assign_condition(
    db: AsyncSession,
    participant: Participant,
    config: dict[str, Any],
    config_hash: str,
) -> ConditionAssignment:
    """Assign a participant to a between-subjects condition.

    Uses round-robin across the conditions list defined in the study config.
    The seed for trial-sequence randomization is deterministic from
    the participant's external_id + config_hash.
    """
    conditions = config.get("conditions", [])
    if not conditions:
        # Single-condition study: use the top-level target
        conditions = [
            {
                "name": "default",
                "target_x": config["stimulus"]["target_x"],
            }
        ]

    # Count existing assignments in this study to determine index
    count_q = select(func.count()).select_from(ConditionAssignment).join(
        Participant, Participant.id == ConditionAssignment.participant_id
    ).where(Participant.study_config_id == participant.study_config_id)
    result = await db.execute(count_q)
    n_assigned = result.scalar_one()

    idx = n_assigned % len(conditions)
    cond = conditions[idx]

    seed = _deterministic_seed(participant.external_id, config_hash)

    assignment = ConditionAssignment(
        participant_id=participant.id,
        condition_name=cond["name"],
        condition_index=idx,
        target_x=cond.get("target_x", config["stimulus"]["target_x"]),
        random_seed=seed,
        assignment_json=cond,
    )
    db.add(assignment)
    await db.flush()
    return assignment
