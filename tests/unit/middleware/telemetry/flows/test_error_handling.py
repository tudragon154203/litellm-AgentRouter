#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import pytest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Request

from src.middleware.telemetry.middleware import TelemetryMiddleware
from src.middleware.telemetry.config import TelemetryConfig
from src.middleware.telemetry.sinks.inmemory import InMemorySink
from src.middleware.telemetry.request_context import NoOpReasoningPolicy


class EnabledToggle:
    def enabled(self, request):
        return True


class TestErrorHandlingFlow:
    """Test exception path with ErrorRaised event emission."""

    def setup_method(self):
        self.log_records = []
        handler = logging.Handler()
        handler.setLevel(logging.DEBUG)
        handler.emit = lambda rec: self.log_records.append(rec)
        self.logger = logging.getLogger("litellm.telemetry")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        self.mock_app = SimpleNamespace(state=SimpleNamespace(litellm_telemetry_alias_lookup={}))
        self.in_memory = InMemorySink()
        self.config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        self.middleware = TelemetryMiddleware(self.mock_app, config=self.config)

    def teardown_method(self):
        if self.log_records:
            self.logger.removeHandler(self.log_records[0])

    def _make_request(self, method="POST", path="/v1/chat/completions", json_body=None):
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(json.dumps({}))).encode())],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "app": self.mock_app,
        }
        req = Request(scope)
        if json_body:
            async def receive():
                return {"type": "http.request", "body": json.dumps(json_body).encode(), "more_body": False}
            req._receive = receive
        return req

    async def test_exception_emits_error_event_and_reraises(self):
        """Test that exceptions emit ErrorRaised event and are re-raised."""
        request = self._make_request(json_body={"model": "test", "stream": False})

        async def call_next(req):
            raise ValueError("Simulated downstream error")

        with patch("time.perf_counter") as mock_time:
            mock_time.side_effect = [0.0, 0.050]

            with pytest.raises(ValueError, match="Simulated downstream error"):
                await self.middleware.dispatch(request, call_next)

        events = self.in_memory.get_events()
        error_events = [e for e in events if e.get("event_type") == "ErrorRaised"]
        assert len(error_events) >= 1, "Should have at least one ErrorRaised event"
        error_event = error_events[0]
        assert error_event["error_type"] == "ValueError"
        assert "Simulated downstream error" in error_event["error_message"]
        assert error_event["duration_s"] == 0.05
