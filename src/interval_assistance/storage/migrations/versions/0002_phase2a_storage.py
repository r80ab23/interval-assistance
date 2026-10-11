"""Phase 2a storage: sensor, recording_session, processing_run, sensor_sample, signal_assessment.

Revision ID: 0002
Revises: 0001

Handwritten and independent of the model definitions: every constraint name is final (`op.f`)
and every value list is repeated here, so the migration keeps its meaning if the models change
later. No indexes beyond those implied by primary keys and the two documented unique
constraints. No defaults, triggers or server-side clocks.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _utc() -> sa.DateTime:
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "sensor",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("external_identifier", sa.String(), nullable=True),
        sa.Column("created_at", _utc(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sensor")),
        sa.CheckConstraint(
            "kind IN ('simulator', 'manual', 'replay')", name=op.f("ck_sensor_kind_values")
        ),
    )

    op.create_table(
        "recording_session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sensor_id", sa.Uuid(), nullable=False),
        sa.Column("source_kind", sa.String(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("started_at", _utc(), nullable=False),
        sa.Column("ended_at", _utc(), nullable=True),
        sa.Column("end_reason", sa.String(), nullable=True),
        sa.Column("signal_quality_config_id", sa.String(), nullable=False),
        sa.Column("signal_quality_config_version", sa.String(), nullable=False),
        sa.Column("signal_quality_config_hash", sa.String(), nullable=False),
        sa.Column("origin_recording_session_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recording_session")),
        sa.ForeignKeyConstraint(
            ["sensor_id"], ["sensor.id"], name=op.f("fk_recording_session_sensor_id_sensor")
        ),
        sa.ForeignKeyConstraint(
            ["origin_recording_session_id"],
            ["recording_session.id"],
            name=op.f("fk_recording_session_origin_session"),
        ),
        sa.CheckConstraint(
            "source_kind IN ('real', 'simulated', 'replay', 'manual')",
            name=op.f("ck_recording_session_source_kind_values"),
        ),
        sa.CheckConstraint(
            "end_reason IS NULL OR end_reason IN ('completed', 'interrupted')",
            name=op.f("ck_recording_session_end_reason_values"),
        ),
    )

    op.create_table(
        "processing_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recording_session_id", sa.Uuid(), nullable=False),
        sa.Column("method_id", sa.String(), nullable=False),
        sa.Column("method_version", sa.String(), nullable=False),
        sa.Column("software_version", sa.String(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("created_at", _utc(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processing_run")),
        sa.ForeignKeyConstraint(
            ["recording_session_id"],
            ["recording_session.id"],
            name=op.f("fk_processing_run_recording_session_id_recording_session"),
        ),
    )

    op.create_table(
        "sensor_sample",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recording_session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("received_hr", sa.Float(), nullable=True),
        sa.Column("received_hr_nonfinite", sa.String(), nullable=True),
        sa.Column("raw_payload", sa.LargeBinary(), nullable=True),
        sa.Column("device_timestamp", _utc(), nullable=True),
        sa.Column("received_at", _utc(), nullable=False),
        sa.Column("ingestion_timestamp", _utc(), nullable=False),
        sa.Column("elapsed_seconds", sa.Float(), nullable=False),
        sa.Column("source_kind", sa.String(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("adapter_quality_hint", sa.Text(), nullable=True),
        sa.Column("origin_sample_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sensor_sample")),
        sa.ForeignKeyConstraint(
            ["recording_session_id"],
            ["recording_session.id"],
            name=op.f("fk_sensor_sample_recording_session_id_recording_session"),
        ),
        sa.ForeignKeyConstraint(
            ["origin_sample_id"],
            ["sensor_sample.id"],
            name=op.f("fk_sensor_sample_origin_sample_id_sensor_sample"),
        ),
        sa.UniqueConstraint(
            "recording_session_id", "sequence", name=op.f("uq_sensor_sample_session_sequence")
        ),
        sa.CheckConstraint("sequence >= 1", name=op.f("ck_sensor_sample_sequence_positive")),
        sa.CheckConstraint(
            "elapsed_seconds >= 0", name=op.f("ck_sensor_sample_elapsed_seconds_non_negative")
        ),
        sa.CheckConstraint(
            "source_kind IN ('real', 'simulated', 'replay', 'manual')",
            name=op.f("ck_sensor_sample_source_kind_values"),
        ),
        sa.CheckConstraint(
            "received_hr_nonfinite IS NULL OR received_hr_nonfinite IN ('nan', '+inf', '-inf')",
            name=op.f("ck_sensor_sample_nonfinite_class_values"),
        ),
        sa.CheckConstraint(
            "received_hr_nonfinite IS NULL OR received_hr IS NULL",
            name=op.f("ck_sensor_sample_nonfinite_excludes_value"),
        ),
    )

    op.create_table(
        "signal_assessment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recording_session_id", sa.Uuid(), nullable=False),
        sa.Column("processing_run_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=True),
        sa.Column("range_start_at", _utc(), nullable=True),
        sa.Column("range_end_at", _utc(), nullable=True),
        sa.Column("after_sample_id", sa.Uuid(), nullable=True),
        sa.Column("before_sample_id", sa.Uuid(), nullable=True),
        sa.Column("quality_state", sa.String(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("created_at", _utc(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_assessment")),
        sa.ForeignKeyConstraint(
            ["recording_session_id"],
            ["recording_session.id"],
            name=op.f("fk_signal_assessment_recording_session_id_recording_session"),
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            ["processing_run.id"],
            name=op.f("fk_signal_assessment_processing_run_id_processing_run"),
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sensor_sample.id"],
            name=op.f("fk_signal_assessment_sample_id_sensor_sample"),
        ),
        sa.ForeignKeyConstraint(
            ["after_sample_id"],
            ["sensor_sample.id"],
            name=op.f("fk_signal_assessment_after_sample_id_sensor_sample"),
        ),
        sa.ForeignKeyConstraint(
            ["before_sample_id"],
            ["sensor_sample.id"],
            name=op.f("fk_signal_assessment_before_sample_id_sensor_sample"),
        ),
        sa.UniqueConstraint(
            "processing_run_id", "sample_id", name=op.f("uq_signal_assessment_run_sample")
        ),
        sa.CheckConstraint(
            "quality_state IN ('UNKNOWN', 'GOOD', 'ACCEPTABLE', 'POOR', 'INVALID', 'STALE',"
            " 'MISSING')",
            name=op.f("ck_signal_assessment_quality_state_values"),
        ),
        sa.CheckConstraint(
            "(sample_id IS NOT NULL AND range_start_at IS NULL AND range_end_at IS NULL"
            " AND after_sample_id IS NULL AND before_sample_id IS NULL)"
            " OR (sample_id IS NULL AND range_start_at IS NOT NULL AND range_end_at IS NOT NULL"
            " AND after_sample_id IS NOT NULL)",
            name=op.f("ck_signal_assessment_single_form"),
        ),
    )


def downgrade() -> None:
    op.drop_table("signal_assessment")
    op.drop_table("sensor_sample")
    op.drop_table("processing_run")
    op.drop_table("recording_session")
    op.drop_table("sensor")
