#!/usr/bin/env python3
from __future__ import annotations


from ..config import TelemetrySink


class InMemorySink(TelemetrySink):
    """In-memory sink for test assertions per PRD."""

    def __init__(self):
        self.events: list[Any] = []

    def emit(self, event: Any) -> None:
        """Store event in list for assertion."""
        self.events.append(event)

    def clear(self) -> None:
        """Clear stored events; useful in test setup."""
        self.events.clear()

    def get_events(self) -> list[Any]:
        """Get a copy of stored events."""
        return self.events.copy()
