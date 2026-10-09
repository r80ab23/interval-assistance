"""Signal validation and stateful quality assessment (Phase 2a).

Pure domain logic: no database, API, hardware or UI dependency. Configuration is explicit and
versioned; no thresholds are defined in code."""

from interval_assistance.signal.canonical import canonical_json, canonical_number
from interval_assistance.signal.config import FORMAT_TAG, SignalQualityConfig, check_identity
from interval_assistance.signal.quality import (
    AssessmentStep,
    RangeFinding,
    SampleAssessment,
    StreamState,
    assess_sample,
    effective_timestamp,
    evaluate_stale,
)
from interval_assistance.signal.reasons import (
    SIGNAL_QUALITY_REASONS,
    STATE_PRECEDENCE,
    VALIDATION_REASONS,
    QualityState,
    ReasonCode,
    worst_state,
)
from interval_assistance.signal.validation import validate_sample

__all__ = [
    "FORMAT_TAG",
    "SIGNAL_QUALITY_REASONS",
    "STATE_PRECEDENCE",
    "VALIDATION_REASONS",
    "AssessmentStep",
    "QualityState",
    "RangeFinding",
    "ReasonCode",
    "SampleAssessment",
    "SignalQualityConfig",
    "StreamState",
    "assess_sample",
    "canonical_json",
    "canonical_number",
    "check_identity",
    "effective_timestamp",
    "evaluate_stale",
    "validate_sample",
    "worst_state",
]
