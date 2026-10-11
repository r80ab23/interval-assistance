"""Insert and select operations for the Phase 2a tables, used by the ingestion service.

Functions take plain storage-level values (never domain objects) and a caller-owned SQLAlchemy
session: they flush so database errors surface immediately, but they never commit or roll back.
Transaction ownership belongs to the application service.

Raw samples and assessments are append-only (DATA_MODEL.md 4.6, 4.7): there is no update or
delete for them. The only update is `close_recording_session`, which sets `ended_at` and
`end_reason` once on an open recording session. Sensors are read but never created here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from interval_assistance.storage.models import (
    ProcessingRun,
    RecordingSession,
    Sensor,
    SensorSample,
    SignalAssessment,
)


def get_sensor(db: Session, sensor_id: uuid.UUID) -> Sensor | None:
    return db.get(Sensor, sensor_id)


def get_recording_session(db: Session, session_id: uuid.UUID) -> RecordingSession | None:
    return db.get(RecordingSession, session_id)


def find_config_hash(db: Session, config_id: str, config_version: str) -> str | None:
    """The hash already recorded for a configuration id and version, or None if never used."""
    statement = (
        select(RecordingSession.signal_quality_config_hash)
        .where(
            RecordingSession.signal_quality_config_id == config_id,
            RecordingSession.signal_quality_config_version == config_version,
        )
        .limit(1)
    )
    return db.execute(statement).scalar_one_or_none()


def insert_recording_session(db: Session, **values: Any) -> RecordingSession:
    row = RecordingSession(**values)
    db.add(row)
    db.flush()
    return row


def insert_processing_run(db: Session, **values: Any) -> ProcessingRun:
    row = ProcessingRun(**values)
    db.add(row)
    db.flush()
    return row


def close_recording_session(
    db: Session, session_id: uuid.UUID, *, ended_at: datetime, end_reason: str
) -> None:
    """Set the end of an open recording session. Raises if it is unknown or already closed."""
    row = db.get(RecordingSession, session_id)
    if row is None:
        raise LookupError(f"unknown recording session: {session_id}")
    if row.ended_at is not None:
        raise ValueError(f"recording session already closed: {session_id}")
    row.ended_at = ended_at
    row.end_reason = end_reason
    db.flush()


def insert_raw_sample(db: Session, **values: Any) -> SensorSample:
    row = SensorSample(**values)
    db.add(row)
    db.flush()
    return row


def insert_signal_assessment(db: Session, **values: Any) -> SignalAssessment:
    row = SignalAssessment(**values)
    db.add(row)
    db.flush()
    return row


def list_raw_samples(db: Session, session_id: uuid.UUID) -> list[SensorSample]:
    statement = (
        select(SensorSample)
        .where(SensorSample.recording_session_id == session_id)
        .order_by(SensorSample.sequence)
    )
    return list(db.execute(statement).scalars())


def list_processing_runs(db: Session, session_id: uuid.UUID) -> list[ProcessingRun]:
    statement = (
        select(ProcessingRun)
        .where(ProcessingRun.recording_session_id == session_id)
        .order_by(ProcessingRun.created_at, ProcessingRun.id)
    )
    return list(db.execute(statement).scalars())


def list_signal_assessments(db: Session, run_id: uuid.UUID) -> list[SignalAssessment]:
    """Assessments of one run, ordered by creation time and then identifier."""
    statement = (
        select(SignalAssessment)
        .where(SignalAssessment.processing_run_id == run_id)
        .order_by(SignalAssessment.created_at, SignalAssessment.id)
    )
    return list(db.execute(statement).scalars())
