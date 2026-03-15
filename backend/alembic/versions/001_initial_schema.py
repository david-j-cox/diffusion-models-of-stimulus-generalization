"""Initial schema — all experiment tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # study_configs
    op.create_table(
        "study_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("config_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("config_json", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # participants
    op.create_table(
        "participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(256), unique=True, nullable=False, index=True),
        sa.Column("study_config_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("study_configs.id"), nullable=False),
        sa.Column("is_pilot", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("participants.id"), nullable=False),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("viewport_width", sa.Integer, nullable=True),
        sa.Column("viewport_height", sa.Integer, nullable=True),
        sa.Column("timezone_offset", sa.Integer, nullable=True),
        sa.Column("is_resume", sa.Boolean, default=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # condition_assignments
    op.create_table(
        "condition_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("participants.id"), unique=True, nullable=False),
        sa.Column("condition_name", sa.String(128), nullable=False),
        sa.Column("condition_index", sa.Integer, nullable=False),
        sa.Column("target_x", sa.Float, nullable=False),
        sa.Column("random_seed", sa.Integer, nullable=False),
        sa.Column("assignment_json", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # trials
    op.create_table(
        "trials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("participants.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("study_config_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("study_configs.id"), nullable=False),
        sa.Column("condition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("condition_assignments.id"), nullable=False),
        # Position
        sa.Column("phase_id", sa.String(64), nullable=False),
        sa.Column("block_index", sa.Integer, nullable=False),
        sa.Column("trial_index_global", sa.Integer, nullable=False),
        sa.Column("trial_index_within_phase", sa.Integer, nullable=False),
        # Stimulus
        sa.Column("stimulus_x_normalized", sa.Float, nullable=False),
        sa.Column("stimulus_render_value", sa.Float, nullable=False),
        sa.Column("stimulus_label", sa.String(32), nullable=False),
        sa.Column("signed_distance_from_target", sa.Float, nullable=False),
        sa.Column("absolute_distance_from_target", sa.Float, nullable=False),
        sa.Column("similarity_gaussian", sa.Float, nullable=False),
        sa.Column("similarity_exponential", sa.Float, nullable=False),
        # Trial parameters
        sa.Column("trial_type", sa.String(32), nullable=False),
        sa.Column("reinforcement_available", sa.Boolean, nullable=False),
        sa.Column("reinforcement_delivered", sa.Boolean, nullable=False),
        sa.Column("feedback_type", sa.String(32), nullable=True),
        # Response
        sa.Column("response_occurred", sa.Boolean, nullable=False),
        sa.Column("response_count", sa.Integer, nullable=False, default=0),
        sa.Column("first_response_rt_ms", sa.Float, nullable=True),
        sa.Column("all_response_timestamps_ms", postgresql.JSONB, nullable=False),
        # Timestamps
        sa.Column("trial_start_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stimulus_onset_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feedback_onset_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end_ts", sa.DateTime(timezone=True), nullable=False),
        # Client
        sa.Column("browser_tz_offset", sa.Integer, nullable=True),
        sa.Column("client_metadata", postgresql.JSONB, nullable=True),
        # Flags
        sa.Column("is_resumed", sa.Boolean, default=False),
        sa.Column("is_attention_check", sa.Boolean, default=False),
        sa.Column("exclusion_flag", sa.String(64), nullable=True),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("random_seed", sa.Integer, nullable=False),
    )
    op.create_index("ix_trials_participant_phase", "trials", ["participant_id", "phase_id"])
    op.create_index("ix_trials_participant_global", "trials", ["participant_id", "trial_index_global"])

    # trial_events
    op.create_table(
        "trial_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trial_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("trials.id"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("key", sa.String(32), nullable=False),
        sa.Column("timestamp_ms", sa.Float, nullable=False),
        sa.Column("relative_to_onset_ms", sa.Float, nullable=False),
    )

    # screen_events
    op.create_table(
        "screen_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("participants.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("event_name", sa.String(128), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # completions
    op.create_table(
        "completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("participants.id"), unique=True, nullable=False),
        sa.Column("completion_code", sa.String(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # exclusions
    op.create_table(
        "exclusions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("participants.id"), nullable=False),
        sa.Column("reason", sa.String(256), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("exclusions")
    op.drop_table("completions")
    op.drop_table("screen_events")
    op.drop_table("trial_events")
    op.drop_index("ix_trials_participant_global", table_name="trials")
    op.drop_index("ix_trials_participant_phase", table_name="trials")
    op.drop_table("trials")
    op.drop_table("condition_assignments")
    op.drop_table("sessions")
    op.drop_table("participants")
    op.drop_table("study_configs")
