"""Recording-session open, sample ingest and explicit close (ARCHITECTURE.md 5.1a).

The service owns the transactions; repositories only add rows. Per sample, the raw row is
committed first (transaction 1), then the assessment is computed and committed (transaction 2).
The in-memory stream state advances only after transaction 2 succeeds, so a failed assessment
leaves a durable raw sample with no assessment (unassessed, never `GOOD`). The next
assessed sample then restarts the comparison (no gap or temporal/jump finding across the
unassessed one). A recording session
exists only in the process that opened it and is ingested by one writer at a time.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from interval_assistance import __version__
from interval_assistance.core.clock import Clock
from interval_assistance.core.errors import InvalidSensorSample
from interval_assistance.core.ids import IdGenerator
from interval_assistance.ingestion.mapping import raw_row_values, to_utc
from interval_assistance.sensors.sample import HeartRateSample, SourceKind
from interval_assistance.signal import (
    RangeFinding,
    SampleAssessment,
    SignalQualityConfig,
    StreamState,
    assess_sample,
    check_identity,
    evaluate_stale,
)
from interval_assistance.storage import repositories

METHOD_ID = "signal_assessment"  # DATA_MODEL.md 4.7
# DATA_MODEL.md 4.7: a string bumped on any rule change. The first value is a project choice.
METHOD_VERSION = "1"
PROCESSING_ACTOR = "system"  # DATA_MODEL.md 2.2
# An explicit close is a normal end. `interrupted` is for a session whose process is gone
# (DATA_MODEL.md 4.4a), which Step 3 does not handle.
CLOSE_END_REASON = "completed"

_SYNTHETIC_SOURCES = frozenset({SourceKind.SIMULATED, SourceKind.MANUAL})


@dataclass(frozen=True, slots=True)
class OpenedSession:
    session_id: uuid.UUID
    processing_run_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class IngestedSample:
    sample_id: uuid.UUID
    sequence: int
    assessment: SampleAssessment
    gap: RangeFinding | None


@dataclass(slots=True)
class _ActiveSession:
    session_id: uuid.UUID
    run_id: uuid.UUID
    sensor_id: uuid.UUID
    source_kind: SourceKind
    is_synthetic: bool
    monotonic_origin: float
    config: SignalQualityConfig
    last_sequence: int = 0
    stream_state: StreamState = field(default_factory=StreamState)
    # `gap` starts after the last assessed arrival.
    last_arrived_sample_id: uuid.UUID | None = None
    # The latest receive time over every committed raw sample, assessed or not, and its sample:
    # a raw row is a fact even without an assessment, so `stale` starts after it.
    max_received_at: datetime | None = None
    max_received_sample_id: uuid.UUID | None = None
    # True after a committed raw sample failed to get its assessment. The stream state then
    # lacks that sample, so the next assessed sample must not be compared with, or bridged to,
    # the older reference (no false gap, duplicate, out-of-order or jump finding).
    unassessed_pending: bool = False


class IngestionService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._factory = session_factory
        self._clock = clock
        self._ids = ids
        self._active: dict[uuid.UUID, _ActiveSession] = {}
        self._closed: set[uuid.UUID] = set()

    def open_session(
        self,
        *,
        sensor_id: uuid.UUID,
        source_kind: SourceKind,
        is_synthetic: bool,
        config: SignalQualityConfig,
    ) -> OpenedSession:
        """Create a recording session and its one processing run in a single transaction.

        The sensor must already be registered; none is created. The session's `is_synthetic`
        is fixed here and every sample must match it."""
        if source_kind is SourceKind.REPLAY:
            raise ValueError("replay sessions are not supported in this step")
        if source_kind in _SYNTHETIC_SOURCES and not is_synthetic:
            raise ValueError("simulated and manual sessions must be flagged synthetic")

        session_id, run_id = self._ids.new_id(), self._ids.new_id()
        started_at = self._clock.now_utc()
        origin = self._clock.monotonic()
        with self._factory() as db, db.begin():
            if repositories.get_sensor(db, sensor_id) is None:
                raise InvalidSensorSample(
                    "unknown sensor", details={"sensor_id": str(sensor_id), "reason": "sensor"}
                )
            check_identity(
                config,
                repositories.find_config_hash(db, config.config_id, config.config_version),
            )
            repositories.insert_recording_session(
                db,
                id=session_id,
                sensor_id=sensor_id,
                source_kind=source_kind.value,
                is_synthetic=is_synthetic,
                started_at=to_utc(started_at),
                ended_at=None,
                end_reason=None,
                signal_quality_config_id=config.config_id,
                signal_quality_config_version=config.config_version,
                signal_quality_config_hash=config.config_hash(),
                origin_recording_session_id=None,
            )
            repositories.insert_processing_run(
                db,
                id=run_id,
                recording_session_id=session_id,
                method_id=METHOD_ID,
                method_version=METHOD_VERSION,
                software_version=__version__,
                parameters=config.hashed_document(),
                created_at=to_utc(started_at),
                actor=PROCESSING_ACTOR,
                is_synthetic=is_synthetic,
            )
        self._active[session_id] = _ActiveSession(
            session_id=session_id,
            run_id=run_id,
            sensor_id=sensor_id,
            source_kind=source_kind,
            is_synthetic=is_synthetic,
            monotonic_origin=origin,
            config=config,
        )
        return OpenedSession(session_id, run_id)

    def ingest(self, session_id: uuid.UUID, sample: HeartRateSample) -> IngestedSample:
        """Persist `sample` as received, then assess it. Raises `InvalidSensorSample` for a
        delivery-contract violation before anything is written or any state moves."""
        active = self._require_active(session_id)
        self._check_delivery(active, sample)

        sequence = active.last_sequence + 1
        sample_id = self._ids.new_id()
        values = raw_row_values(
            sample,
            sample_id=sample_id,
            session_id=session_id,
            sequence=sequence,
            ingestion_timestamp=self._clock.now_utc(),
            elapsed_seconds=self._clock.monotonic() - active.monotonic_origin,
        )

        # Transaction 1: the raw row, before validation or signal quality.
        with self._factory() as db, db.begin():
            repositories.insert_raw_sample(db, **values)
        active.last_sequence = sequence  # the row exists, so its sequence is spent
        received_at = to_utc(sample.received_at)
        if active.max_received_at is None or received_at > active.max_received_at:
            active.max_received_at, active.max_received_sample_id = received_at, sample_id

        try:
            # After an unassessed sample the stream restarts here: no earlier reference is
            # compared with this sample, so nothing is concluded across the missing one.
            reference = StreamState() if active.unassessed_pending else active.stream_state
            step = assess_sample(sample, reference, active.config)

            # Transaction 2: the assessment and any gap range.
            with self._factory() as db, db.begin():
                created_at = to_utc(self._clock.now_utc())
                repositories.insert_signal_assessment(
                    db,
                    **self._assessment_values(
                        active,
                        created_at,
                        sample_id=sample_id,
                        quality_state=step.assessment.state.value,
                        reasons=[reason.value for reason in step.assessment.reasons],
                    ),
                )
                if step.gap is not None:
                    repositories.insert_signal_assessment(
                        db,
                        **self._assessment_values(
                            active,
                            created_at,
                            quality_state=step.gap.state.value,
                            reasons=[step.gap.reason.value],
                            range_start_at=step.gap.start,
                            range_end_at=step.gap.end,
                            after_sample_id=active.last_arrived_sample_id,
                            before_sample_id=sample_id,
                        ),
                    )
        except Exception:
            active.unassessed_pending = True  # stream state stays as it was
            raise

        # Only now does the stream move on. The stale reference stays the maximum over all
        # committed raw samples, including any unassessed ones.
        state = step.next_state
        if active.max_received_at is not None:
            state = replace(state, max_received_at=active.max_received_at)
        active.stream_state = state
        active.unassessed_pending = False
        active.last_arrived_sample_id = sample_id
        return IngestedSample(sample_id, sequence, step.assessment, step.gap)

    def close(self, session_id: uuid.UUID) -> None:
        """End the session. Persists the open `stale` range if the latest receive time is older
        than the configured limit at the injected closing time. If the transaction fails the
        session stays open."""
        active = self._require_active(session_id)
        now = to_utc(self._clock.now_utc())
        stale = (
            None
            if active.max_received_at is None
            else evaluate_stale(active.max_received_at, now, active.config)
        )
        with self._factory() as db, db.begin():
            if stale is not None:
                repositories.insert_signal_assessment(
                    db,
                    **self._assessment_values(
                        active,
                        now,
                        quality_state=stale.state.value,
                        reasons=[stale.reason.value],
                        range_start_at=stale.start,
                        range_end_at=stale.end,
                        after_sample_id=active.max_received_sample_id,
                        before_sample_id=None,
                    ),
                )
            repositories.close_recording_session(
                db, session_id, ended_at=now, end_reason=CLOSE_END_REASON
            )
        del self._active[session_id]
        self._closed.add(session_id)

    def _require_active(self, session_id: uuid.UUID) -> _ActiveSession:
        active = self._active.get(session_id)
        if active is not None:
            return active
        reason = "closed" if session_id in self._closed else "unknown_or_inactive"
        raise InvalidSensorSample(
            f"recording session is not active: {reason}",
            details={"session_id": str(session_id), "reason": reason},
        )

    @staticmethod
    def _check_delivery(active: _ActiveSession, sample: HeartRateSample) -> None:
        mismatches = {
            "sensor": sample.sensor_id != active.sensor_id,
            "source_kind": sample.source_kind is not active.source_kind,
            "is_synthetic": sample.is_synthetic != active.is_synthetic,
        }
        for reason, mismatched in mismatches.items():
            if mismatched:
                raise InvalidSensorSample(
                    f"sample does not match its recording session: {reason}",
                    details={"session_id": str(active.session_id), "reason": reason},
                )

    def _assessment_values(
        self, active: _ActiveSession, created_at: datetime, **fields: Any
    ) -> dict[str, Any]:
        """Columns of one assessment row; the per-sample and range columns default to NULL."""
        return {
            "id": self._ids.new_id(),
            "recording_session_id": active.session_id,
            "processing_run_id": active.run_id,
            "sample_id": None,
            "range_start_at": None,
            "range_end_at": None,
            "after_sample_id": None,
            "before_sample_id": None,
            "created_at": created_at,
        } | fields
