#!/usr/bin/env python3
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout

from src.middleware.telemetry.sinks.console import ConsoleSink


class TestConsoleSink:
    """Test console sink output."""

    def test_emit_writes_to_stdout(self):
        """ConsoleSink should write events to stdout."""
        sink = ConsoleSink()
        captured = io.StringIO()

        with redirect_stdout(captured):
            sink.emit({"event": "test", "value": 123})

        output = captured.getvalue()
        assert "event" in output
        assert "test" in output
        assert "123" in output

    def test_emit_handles_string_events(self):
        """ConsoleSink should handle string events."""
        sink = ConsoleSink()
        captured = io.StringIO()

        with redirect_stdout(captured):
            sink.emit("simple string event")

        output = captured.getvalue()
        assert "simple string event" in output

    def test_emit_handles_complex_objects(self):
        """ConsoleSink should handle complex nested objects."""
        sink = ConsoleSink()
        captured = io.StringIO()

        event = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "mixed": {"a": [{"b": "c"}]}
        }

        with redirect_stdout(captured):
            sink.emit(event)

        output = captured.getvalue()
        assert "nested" in output
