#!/usr/bin/env python3
from __future__ import annotations

from src.middleware.telemetry.sinks.inmemory import InMemorySink


class TestInMemorySink:
    """Test in-memory sink captures and assertions."""

    def test_sink_stores_and_returns_events(self):
        """Sink should store events and provide access."""
        sink = InMemorySink()
        events = [{"type": "a"}, {"type": "b"}]
        for e in events:
            sink.emit(e)
        assert sink.get_events() == events

    def test_clear_empties_events(self):
        """Clear should reset stored events."""
        sink = InMemorySink()
        sink.emit({"type": "before"})
        assert sink.get_events() == [{"type": "before"}]
        sink.clear()
        assert sink.get_events() == []

    def test_returns_copy_not_reference(self):
        """get_events should return copy to prevent external mutation."""
        sink = InMemorySink()
        sink.emit({"type": "test"})
        events1 = sink.get_events()
        events2 = sink.get_events()
        assert events1 == events2
        assert events1 is not events2  # separate lists
