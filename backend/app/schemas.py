"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Registration ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=256)
    user_agent: str | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    timezone_offset: int | None = None


class ConditionInfo(BaseModel):
    condition_name: str
    condition_index: int
    target_x: float
    random_seed: int
    assignment: dict


class RegisterResponse(BaseModel):
    participant_id: uuid.UUID
    session_id: uuid.UUID
    condition: ConditionInfo
    study_config: dict
    resume_from_trial: int | None = None


# ── Session (resume) ─────────────────────────────────────────────────────────

class ResumeRequest(BaseModel):
    participant_id: uuid.UUID
    user_agent: str | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    timezone_offset: int | None = None


class ResumeResponse(BaseModel):
    session_id: uuid.UUID
    resume_from_trial: int


# ── Trial submission ──────────────────────────────────────────────────────────

class TrialEventPayload(BaseModel):
    event_type: str
    key: str
    timestamp_ms: float
    relative_to_onset_ms: float


class TrialPayload(BaseModel):
    """Client sends this after each trial completes."""

    phase_id: str
    block_index: int
    trial_index_global: int
    trial_index_within_phase: int

    stimulus_x_normalized: float
    stimulus_render_value: float
    stimulus_label: str
    signed_distance_from_target: float
    absolute_distance_from_target: float
    similarity_gaussian: float
    similarity_exponential: float

    trial_type: str
    reinforcement_available: bool
    reinforcement_delivered: bool
    feedback_type: str | None = None

    response_occurred: bool
    response_count: int = 0
    first_response_rt_ms: float | None = None
    all_response_timestamps_ms: list[float] = Field(default_factory=list)

    trial_start_ts: str  # ISO-8601
    stimulus_onset_ts: str
    feedback_onset_ts: str | None = None
    trial_end_ts: str

    browser_tz_offset: int | None = None
    client_metadata: dict | None = None
    is_resumed: bool = False
    is_attention_check: bool = False

    events: list[TrialEventPayload] = Field(default_factory=list)


class TrialBatchPayload(BaseModel):
    """Batch of trials for durable sync."""

    participant_id: uuid.UUID
    session_id: uuid.UUID
    trials: list[TrialPayload]


class TrialBatchResponse(BaseModel):
    saved_count: int
    next_expected_trial: int


# ── Screen events ─────────────────────────────────────────────────────────────

class ScreenEventPayload(BaseModel):
    participant_id: uuid.UUID
    session_id: uuid.UUID
    event_name: str
    metadata_json: dict | None = None
    timestamp: str  # ISO-8601


# ── Completion ────────────────────────────────────────────────────────────────

class CompleteRequest(BaseModel):
    participant_id: uuid.UUID


class CompleteResponse(BaseModel):
    completion_code: str


# ── Admin ─────────────────────────────────────────────────────────────────────

class ParticipantSummary(BaseModel):
    id: uuid.UUID
    external_id: str
    condition_name: str | None = None
    trial_count: int
    is_pilot: bool
    completed: bool
    excluded: bool
    created_at: datetime


class ExcludeRequest(BaseModel):
    participant_id: uuid.UUID
    reason: str
    source: str = "manual"


class StudyConfigSummary(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    config_hash: str
    created_at: datetime
