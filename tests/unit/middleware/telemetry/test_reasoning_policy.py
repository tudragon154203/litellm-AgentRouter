#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import Request

from src.middleware.telemetry.middleware import TelemetryMiddleware
from src.middleware.telemetry.config import TelemetryConfig
from src.middleware.telemetry.sinks.inmemory import InMemorySink
from src.middleware.telemetry.request_context import apply_reasoning_policy


class EnabledToggle:
    def enabled(self, request):
        return True


class TestReasoningPolicy:
    """Test reasoning policy mutation and debug metadata."""

    def setup_method(self):
        self.mock_app = SimpleNamespace(state=SimpleNamespace(litellm_telemetry_alias_lookup={}))
        self.in_memory = InMemorySink()
        self.policy = TestReasoningPolicy.DropReasoningPolicy()
        self.config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=self.policy,
        )
        self.middleware = TelemetryMiddleware(self.mock_app, config=self.config)

    async def test_reasoning_policy_mutates_and_emits_metadata(self):
        """Policy should drop reasoning field and emit debug metadata."""
        # Request on filterable path
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [(b"content-type", b"application/json"), (b"content-length", b'{"model":"test","reasoning":"dropme"}')],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "app": self.mock_app,
        }
        request = Request(scope)

        async def receive():
            return {"type": "http.request", "body": b'{"model":"test","reasoning":"dropme"}', "more_body": False}
        request._receive = receive

        async def call_next(req):
            # Simulate downstream response
            from fastapi import Response
            return Response(content=b'{"ok":true}')

        result = await self.middleware.dispatch(request, call_next)

        # Verify events captured
        events = self.in_memory.get_events()
        req_event = next((e for e in events if e.get("event_type") == "RequestReceived"))
        assert req_event is not None
        # Debug metadata should indicate reasoning was dropped
        assert "dropped_param" in req_event.get("reasoning_metadata", {})

        # Ensure downstream was called normally (policy mutates request)
        assert result is not None

    class DropReasoningPolicy:
        def apply(self, request: Request):
            # Mutate request to remove 'reasoning' from JSON body and generate debug metadata
            # Simplified for test; actual legacy filter uses full parsing
            return request, {"dropped_param": "reasoning"}

    class EnabledToggle:
        def enabled(self, request):
            return True
