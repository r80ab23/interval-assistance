"""Phase 2a persistence schema: exactly five tables (docs/DATA_MODEL.md 4.4a, 4.6, 4.7, 2.2).

Models carry no business logic and no defaults: identifiers, timestamps and flags are supplied
by the caller (injected `IdGenerator` and `Clock`). Only constraints stated in the data model are
declared. Rules the data model assigns to ingestion (gap-free sequence, session/sample
consistency, config-string patterns, append-only access) are deliberately not database rules.

The value lists below are local literals because `storage` may not import `sensors` or `signal`;
tests outside the package check them against the domain enums. Migration `0002` repeats every
name and literal by hand and does not import this module.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from interval_assistance.storage.base import Base

SENSOR_KINDS = ("simulator", "manual", "replay")
SOURCE_KINDS = ("real", "simulated", "replay", "manual")
END_REASONS = ("completed", "interrupted")
NONFINITE_CLASSES = ("nan", "+inf", "-inf")
QUALITY_STATES = ("UNKNOWN", "GOOD", "ACCEPTABLE", "POOR", "INVALID", "STALE", "MISSING")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _utc() -> DateTime:
    return DateTime(timezone=True)


class Sensor(Base):
    __tablename__ = "sensor"
    __table_args__ = (CheckConstraint(_in("kind", SENSOR_KINDS), name="kind_values"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    external_identifier: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(_utc(), nullable=False)


class RecordingSession(Base):
    __tablename__ = "recording_session"
    __table_args__ = (
        CheckConstraint(_in("source_kind", SOURCE_KINDS), name="source_kind_values"),
        CheckConstraint(
            "end_reason IS NULL OR " + _in("end_reason", END_REASONS), name="end_reason_values"
        ),
        # Explicit name: the generated one would exceed PostgreSQL's 63-character limit.
        ForeignKeyConstraint(
            ["origin_recording_session_id"],
            ["recording_session.id"],
            name="fk_recording_session_origin_session",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    sensor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sensor.id"), nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    started_at: Mapped[datetime] = mapped_column(_utc(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(_utc(), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    signal_quality_config_id: Mapped[str] = mapped_column(String, nullable=False)
    signal_quality_config_version: Mapped[str] = mapped_column(String, nullable=False)
    signal_quality_config_hash: Mapped[str] = mapped_column(String, nullable=False)
    origin_recording_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class ProcessingRun(Base):
    __tablename__ = "processing_run"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    recording_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recording_session.id"), nullable=False
    )
    method_id: Mapped[str] = mapped_column(String, nullable=False)
    method_version: Mapped[str] = mapped_column(String, nullable=False)
    software_version: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(_utc(), nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SensorSample(Base):
    __tablename__ = "sensor_sample"
    __table_args__ = (
        UniqueConstraint(
            "recording_session_id", "sequence", name="uq_sensor_sample_session_sequence"
        ),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
        CheckConstraint("elapsed_seconds >= 0", name="elapsed_seconds_non_negative"),
        CheckConstraint(_in("source_kind", SOURCE_KINDS), name="source_kind_values"),
        CheckConstraint(
            "received_hr_nonfinite IS NULL OR " + _in("received_hr_nonfinite", NONFINITE_CLASSES),
            name="nonfinite_class_values",
        ),
        # One-way only: a set class implies a NULL value. Finite-value validation and the
        # non-finite-to-marker conversion are enforced by ingestion, not by the database.
        CheckConstraint(
            "received_hr_nonfinite IS NULL OR received_hr IS NULL", name="nonfinite_excludes_value"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    recording_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recording_session.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    received_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    received_hr_nonfinite: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_payload: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    device_timestamp: Mapped[datetime | None] = mapped_column(_utc(), nullable=True)
    received_at: Mapped[datetime] = mapped_column(_utc(), nullable=False)
    ingestion_timestamp: Mapped[datetime] = mapped_column(_utc(), nullable=False)
    elapsed_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    adapter_quality_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_sample_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sensor_sample.id"), nullable=True
    )


class SignalAssessment(Base):
    __tablename__ = "signal_assessment"
    __table_args__ = (
        # No partial index and no NULLS NOT DISTINCT: NULL sample_id pairs stay distinct, so the
        # constraint covers per-sample rows only (DATA_MODEL.md 4.7).
        UniqueConstraint("processing_run_id", "sample_id", name="uq_signal_assessment_run_sample"),
        CheckConstraint(_in("quality_state", QUALITY_STATES), name="quality_state_values"),
        # Exactly one form per row: per-sample, or range (before_sample_id NULL when open-ended).
        CheckConstraint(
            "(sample_id IS NOT NULL AND range_start_at IS NULL AND range_end_at IS NULL"
            " AND after_sample_id IS NULL AND before_sample_id IS NULL)"
            " OR (sample_id IS NULL AND range_start_at IS NOT NULL AND range_end_at IS NOT NULL"
            " AND after_sample_id IS NOT NULL)",
            name="single_form",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    recording_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recording_session.id"), nullable=False
    )
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processing_run.id"), nullable=False
    )
    sample_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sensor_sample.id"), nullable=True
    )
    range_start_at: Mapped[datetime | None] = mapped_column(_utc(), nullable=True)
    range_end_at: Mapped[datetime | None] = mapped_column(_utc(), nullable=True)
    after_sample_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sensor_sample.id"), nullable=True
    )
    before_sample_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sensor_sample.id"), nullable=True
    )
    quality_state: Mapped[str] = mapped_column(String, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(_utc(), nullable=False)
