#!/usr/bin/env python3
from __future__ import annotations

from types import SimpleNamespace

from src.middleware.telemetry.middleware import TelemetryMiddleware
from src.middleware.telemetry.config import TelemetryConfig
from src.middleware.telemetry.sinks.inmemory import InMemorySink
from src.middleware.telemetry.request_context import NoOpReasoningPolicy


class TestInMemorySink:
    """Test in-memory sink captures and assertions."""

    def setup_method(self):
        self.mock_app = SimpleNamespace(state=SimpleNamespace(litellm_telemetry_alias_lookup={}))
        self.sink = InMemorySink()
        self.config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.sink],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        self.middleware = TelemetryMiddleware(self.mock_app, config=self.config)

    def test_sink_stores_and_returns_events(self):
        """Sink should store events and provide access."""
        events = [{"type": "a"}, {"type": "b"}]
        for e in events:
            self.sink.emit(e)
        assert self.sink.get_events() == events

    def test_clear_empties_events(self):
        """Clear should reset stored events."""
        self.sink.emit({"type": "before"})
        assert self.sink.get_events() == [{"type": "before"}]
        self.sink.clear()
        assert self.sink.get_events() == []

    def test_returns_copy_not_reference(self):
        """get_events should return copy to prevent external mutation."""
        self.sink.emit({"type": "test"})
        events1 = self.sink.get_events()
        events2 = self.sink.get_events()
        assert events1 == events2
        assert events1 is not events2  # separate lists


class EnabledToggle:
    def enabled(self, request):
        return True
