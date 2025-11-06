#!/usr/bin/env python3
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Request, Response

from src.middleware.telemetry.middleware import TelemetryMiddleware
from src.middleware.telemetry.config import TelemetryConfig
from src.middleware.telemetry.sinks.inmemory import InMemorySink


class TestIsolation:
    """Verify new telemetry pipeline works independently without shared class state."""

    async def test_new_middleware_with_explicit_config(self):
        """TelemetryMiddleware works with explicit TelemetryConfig."""
        mock_app = SimpleNamespace(state=SimpleNamespace(litellm_telemetry_alias_lookup={}))
        sink = InMemorySink()
        config = TelemetryConfig(
            toggle=AlwaysEnabled(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[sink],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(app=mock_app, config=config)

        request = self._make_request()

        async def call_next(req):
            return Response(content=b'{"ok":true}')

        with patch("time.perf_counter") as mock_time:
            mock_time.side_effect = [0.0, 0.100]
            result = await middleware.dispatch(request, call_next)

        assert result is not None
        events = sink.get_events()
        assert any(e.get("event_type") == "RequestReceived" for e in events)
        assert any(e.get("event_type") == "ResponseCompleted" for e in events)

    def _make_request(self, json_body=None):
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(json.dumps(json_body or {}))).encode())],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
        }
        req = Request(scope)
        if json_body:
            async def receive():
                return {"type": "http.request", "body": json.dumps(json_body).encode(), "more_body": False}
            req._receive = receive
        return req


class AlwaysEnabled:
    def enabled(self, request):
        return True


class NoOpReasoningPolicy:
    def apply(self, request):
        return request, {}
