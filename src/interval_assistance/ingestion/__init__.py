"""Raw sample intake and durable signal assessment (Part 2a, ARCHITECTURE.md 5.1a).

Application layer: it may use `core`, `sensors`, `signal` and `storage`; none of them may import
it. Raw samples are committed before assessment; there is no replay, API or config loading here.
"""

from interval_assistance.ingestion.service import (
    CLOSE_END_REASON,
    METHOD_ID,
    METHOD_VERSION,
    PROCESSING_ACTOR,
    IngestedSample,
    IngestionService,
    OpenedSession,
)

__all__ = [
    "CLOSE_END_REASON",
    "METHOD_ID",
    "METHOD_VERSION",
    "PROCESSING_ACTOR",
    "IngestedSample",
    "IngestionService",
    "OpenedSession",
]
