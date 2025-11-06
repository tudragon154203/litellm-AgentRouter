#!/usr/bin/env python3
from __future__ import annotations

import logging

from src.middleware.telemetry.pipeline import TelemetryPipeline
from src.middleware.telemetry.sinks.inmemory import InMemorySink


class TestTelemetryPipeline:
    """Test telemetry pipeline fan-out and isolation."""

    def setup_method(self):
        self.log_records = []
        handler = logging.Handler()
        handler.setLevel(logging.WARNING)
        handler.emit = lambda rec: self.log_records.append(rec)
        self.logger = logging.getLogger("litellm_launcher.telemetry.pipeline")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.WARNING)
        self.logger.propagate = False

    def teardown_method(self):
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

    def test_publish_emits_to_all_sinks(self):
        """Pipeline should emit to all configured sinks."""
        sink1 = InMemorySink()
        sink2 = InMemorySink()
        pipeline = TelemetryPipeline([sink1, sink2])

        event = {"type": "test", "value": 42}
        pipeline.publish(event)

        assert sink1.get_events() == [event]
        assert sink2.get_events() == [event]

    def test_publish_with_no_sinks_does_nothing(self):
        """Pipeline with no sinks should not error."""
        pipeline = TelemetryPipeline([])

        # Should not raise
        pipeline.publish({"type": "test"})

    def test_publish_isolates_sink_failures(self):
        """Pipeline should continue to other sinks if one fails."""
        class FailingSink:
            def emit(self, event):
                raise RuntimeError("Sink failure")

        failing_sink = FailingSink()
        working_sink = InMemorySink()
        pipeline = TelemetryPipeline([failing_sink, working_sink])

        event = {"type": "test"}
        pipeline.publish(event)

        # Working sink should still receive event
        assert working_sink.get_events() == [event]

        # Should log warning about failure
        assert len(self.log_records) == 1
        assert "FailingSink" in self.log_records[0].getMessage()
        assert "failed" in self.log_records[0].getMessage().lower()

    def test_publish_continues_after_multiple_failures(self):
        """Pipeline should continue even if multiple sinks fail."""
        class FailingSink:
            def emit(self, event):
                raise ValueError("Fail")

        sink1 = FailingSink()
        sink2 = InMemorySink()
        sink3 = FailingSink()
        sink4 = InMemorySink()

        pipeline = TelemetryPipeline([sink1, sink2, sink3, sink4])
        event = {"type": "test"}
        pipeline.publish(event)

        # Working sinks should receive event
        assert sink2.get_events() == [event]
        assert sink4.get_events() == [event]

        # Should log two warnings
        assert len(self.log_records) == 2
