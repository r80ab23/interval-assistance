"""Identifier generation. UUIDs are the approved identifier strategy."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod


class IdGenerator(ABC):
    @abstractmethod
    def new_id(self) -> uuid.UUID:
        """Return a new identifier."""


class UuidGenerator(IdGenerator):
    """Random (version 4) UUIDs. The UUID version is a recorded Phase 1 choice."""

    def new_id(self) -> uuid.UUID:
        return uuid.uuid4()


class SequentialIdGenerator(IdGenerator):
    """Deterministic ids (counter-based) for tests and reproducible runs."""

    def __init__(self, start: int = 1) -> None:
        self._next = start

    def new_id(self) -> uuid.UUID:
        value = uuid.UUID(int=self._next)
        self._next += 1
        return value
