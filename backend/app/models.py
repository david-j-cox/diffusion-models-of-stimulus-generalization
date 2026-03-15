"""SQLAlchemy ORM models for the stimulus generalization experiment.

Tables
------
- study_configs: immutable snapshots of YAML study configurations
- participants: one row per human participant
- sessions: browser sessions (a participant may have multiple if they resume)
- condition_assignments: maps participant -> condition within a study
- trials: the core behavioral data table — one row per trial
- trial_events: sub-trial keypress events (all responses within a window)
- screen_events: consent, instructions, phase transitions, etc.
- completions: completion codes issued
- exclusions: researcher-applied or automated exclusion flags
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class StudyConfig(Base):
    """Immutable snapshot of a study YAML config."""

    __tablename__ = "study_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participants: Mapped[list[Participant]] = relationship(back_populates="study_config")


class Participant(Base):
    """One row per human participant."""

    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    external_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    study_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("study_configs.id"), nullable=False
    )
    is_pilot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    study_config: Mapped[StudyConfig] = relationship(back_populates="participants")
    sessions: Mapped[list[Session]] = relationship(back_populates="participant")
    condition_assignment: Mapped[ConditionAssignment | None] = relationship(
        back_populates="participant", uselist=False
    )
    trials: Mapped[list[Trial]] = relationship(back_populates="participant")
    screen_events: Mapped[list[ScreenEvent]] = relationship(back_populates="participant")
    completion: Mapped[Completion | None] = relationship(back_populates="participant", uselist=False)
    exclusions: Mapped[list[Exclusion]] = relationship(back_populates="participant")


class Session(Base):
    """Browser session. A participant gets a new session on each page load / resume."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    viewport_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_resume: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participant: Mapped[Participant] = relationship(back_populates="sessions")
    trials: Mapped[list[Trial]] = relationship(back_populates="session")


class ConditionAssignment(Base):
    """Maps a participant to a between-subjects condition."""

    __tablename__ = "condition_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id"), unique=True, nullable=False
    )
    condition_name: Mapped[str] = mapped_column(String(128), nullable=False)
    condition_index: Mapped[int] = mapped_column(Integer, nullable=False)
    target_x: Mapped[float] = mapped_column(Float, nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    assignment_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participant: Mapped[Participant] = relationship(back_populates="condition_assignment")


class Trial(Base):
    """Core behavioural data — one row per trial."""

    __tablename__ = "trials"
    __table_args__ = (
        Index("ix_trials_participant_phase", "participant_id", "phase_id"),
        Index("ix_trials_participant_global", "participant_id", "trial_index_global"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    study_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("study_configs.id"), nullable=False
    )
    condition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("condition_assignments.id"), nullable=False
    )

    # Position in sequence
    phase_id: Mapped[str] = mapped_column(String(64), nullable=False)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    trial_index_global: Mapped[int] = mapped_column(Integer, nullable=False)
    trial_index_within_phase: Mapped[int] = mapped_column(Integer, nullable=False)

    # Stimulus
    stimulus_x_normalized: Mapped[float] = mapped_column(Float, nullable=False)
    stimulus_render_value: Mapped[float] = mapped_column(Float, nullable=False)
    stimulus_label: Mapped[str] = mapped_column(String(32), nullable=False)  # S+, S-, probe, practice
    signed_distance_from_target: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_distance_from_target: Mapped[float] = mapped_column(Float, nullable=False)
    similarity_gaussian: Mapped[float] = mapped_column(Float, nullable=False)
    similarity_exponential: Mapped[float] = mapped_column(Float, nullable=False)

    # Trial parameters
    trial_type: Mapped[str] = mapped_column(String(32), nullable=False)  # training, probe, practice, discrimination
    reinforcement_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reinforcement_delivered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Response data
    response_occurred: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_response_rt_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    all_response_timestamps_ms: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Timestamps (UTC)
    trial_start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stimulus_onset_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feedback_onset_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Client metadata
    browser_tz_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Flags
    is_resumed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_attention_check: Mapped[bool] = mapped_column(Boolean, default=False)
    exclusion_flag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)

    participant: Mapped[Participant] = relationship(back_populates="trials")
    session: Mapped[Session] = relationship(back_populates="trials")
    events: Mapped[list[TrialEvent]] = relationship(back_populates="trial")


class TrialEvent(Base):
    """Individual keypress or response event within a trial."""

    __tablename__ = "trial_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    trial_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trials.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # keydown, keyup
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp_ms: Mapped[float] = mapped_column(Float, nullable=False)
    relative_to_onset_ms: Mapped[float] = mapped_column(Float, nullable=False)

    trial: Mapped[Trial] = relationship(back_populates="events")


class ScreenEvent(Base):
    """Screen-level lifecycle events (consent, instructions, phase transitions, etc.)."""

    __tablename__ = "screen_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participant: Mapped[Participant] = relationship(back_populates="screen_events")


class Completion(Base):
    """Completion code issued to participant."""

    __tablename__ = "completions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id"), unique=True, nullable=False
    )
    completion_code: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participant: Mapped[Participant] = relationship(back_populates="completion")


class Exclusion(Base):
    """Exclusion flags — automated or researcher-applied. Never deletes participant data."""

    __tablename__ = "exclusions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)  # auto, manual
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participant: Mapped[Participant] = relationship(back_populates="exclusions")
