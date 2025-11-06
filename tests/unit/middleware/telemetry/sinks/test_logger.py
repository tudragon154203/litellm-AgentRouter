#!/usr/bin/env python3
from __future__ import annotations

import json
import logging

from src.middleware.telemetry.sinks.logger import LoggerSink
from src.middleware.telemetry.events import UsageTokens


class TestLoggerSink:
    """Test logger sink JSON serialization."""

    def setup_method(self):
        self.log_records = []
        handler = logging.Handler()
        handler.setLevel(logging.INFO)
        handler.emit = lambda rec: self.log_records.append(rec)
        self.logger = logging.getLogger("test.logger.sink")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def teardown_method(self):
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

    def test_emit_logs_response_completed_event(self):
        """LoggerSink should log ResponseCompleted events."""
        sink = LoggerSink("test.logger.sink")
        event = {
            "event_type": "ResponseCompleted",
            "duration_s": 0.5,
            "status_code": 200,
            "usage": UsageTokens(total=100, prompt=40, completion=60, reasoning=None)
        }

        sink.emit(event)

        assert len(self.log_records) == 1
        record = self.log_records[0]
        assert record.levelno == logging.INFO
        logged = json.loads(record.getMessage())
        # event_type is removed from output, status_code is first
        assert "event_type" not in logged
        assert logged["status_code"] == 200
        assert logged["duration_s"] == 0.5  # rounded to 2 decimals
        assert logged["usage"]["total_tokens"] == 100
        assert logged["usage"]["prompt_tokens"] == 40

    def test_emit_ignores_non_response_completed_events(self):
        """LoggerSink should ignore RequestReceived events."""
        sink = LoggerSink("test.logger.sink")
        event = {
            "event_type": "RequestReceived",
            "method": "POST",
            "path": "/v1/chat/completions"
        }

        sink.emit(event)

        assert len(self.log_records) == 0

    def test_emit_handles_usage_tokens_conversion(self):
        """LoggerSink should convert UsageTokens to dict."""
        sink = LoggerSink("test.logger.sink")
        event = {
            "event_type": "ResponseCompleted",
            "usage": UsageTokens(total=50, prompt=20, completion=30, reasoning=10)
        }

        sink.emit(event)

        assert len(self.log_records) == 1
        logged = json.loads(self.log_records[0].getMessage())
        assert logged["usage"]["reasoning_tokens"] == 10

    def test_emit_handles_nested_dicts(self):
        """LoggerSink should handle nested dictionaries."""
        sink = LoggerSink("test.logger.sink")
        event = {
            "event_type": "ResponseCompleted",
            "metadata": {
                "nested": {"key": "value"},
                "list": [1, 2, 3]
            }
        }

        sink.emit(event)

        assert len(self.log_records) == 1
        logged = json.loads(self.log_records[0].getMessage())
        assert logged["metadata"]["nested"]["key"] == "value"

    def test_emit_handles_serialization_failure(self):
        """LoggerSink should fallback on serialization failure."""
        sink = LoggerSink("test.logger.sink")

        # Create an object that can't be serialized
        class UnserializableObject:
            def __str__(self):
                return "unserializable"

        event = {
            "event_type": "ResponseCompleted",
            "bad_field": UnserializableObject()
        }

        sink.emit(event)

        # Should still log something (the convert function handles objects with __dict__)
        assert len(self.log_records) == 1
        message = self.log_records[0].getMessage()
        # The object gets converted to dict, event_type is removed
        logged = json.loads(message)
        assert "bad_field" in logged
        assert "event_type" not in logged
