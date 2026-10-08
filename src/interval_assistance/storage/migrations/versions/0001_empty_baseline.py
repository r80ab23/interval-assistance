"""Empty baseline. Phase 1 creates no tables.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Intentionally empty: raw sample persistence and domain tables belong to later phases."""


def downgrade() -> None:
    """Intentionally empty."""
