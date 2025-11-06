#!/usr/bin/env python3
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

from fastapi import Request, Response

from src.middleware.telemetry.middleware import TelemetryMiddleware
from src.middleware.telemetry.config import TelemetryConfig
from src.middleware.telemetry.sinks.inmemory import InMemorySink
from src.middleware.telemetry.request_context import NoOpReasoningPolicy


class TestMiddlewareBranches:
    """Test uncovered branches in TelemetryMiddleware."""

    def setup_method(self):
        self.mock_app = SimpleNamespace(state=SimpleNamespace(litellm_telemetry_alias_lookup={}))
        self.in_memory = InMemorySink()

    def _make_request(self, method="POST", path="/v1/chat/completions", json_body=None, headers=None):
        default_headers = [(b"content-type", b"application/json")]
        if headers:
            default_headers.extend(headers)

        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": default_headers,
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

    def _make_response(self, status_code=200, json_body=None):
        content = (json.dumps(json_body) if json_body else "{}").encode()
        resp = Response(content=content, media_type="application/json")
        resp.status_code = status_code
        resp.body = content
        return resp

    async def test_toggle_exception_defaults_to_enabled(self):
        """If toggle.enabled() raises, should default to enabled."""
        class FailingToggle:
            def enabled(self, request):
                raise RuntimeError("Toggle failure")

        config = TelemetryConfig(
            toggle=FailingToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(self.mock_app, config=config)

        request = self._make_request(json_body={"model": "test"})
        response = self._make_response(200, {"usage": {"prompt_tokens": 5, "completion_tokens": 10}})

        async def call_next(req):
            return response

        result = await middleware.dispatch(request, call_next)

        # Should still process (default to enabled)
        assert result is response
        # Should have emitted events
        assert len(self.in_memory.get_events()) > 0

    async def test_request_without_json_body(self):
        """Handle requests that don't have JSON body."""
        config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(self.mock_app, config=config)

        # Request without JSON body
        request = self._make_request(method="GET", path="/health")
        response = self._make_response(200)

        async def call_next(req):
            return response

        result = await middleware.dispatch(request, call_next)

        assert result is response
        # Should use "unknown" as model alias
        events = self.in_memory.get_events()
        assert any(e.get("event_type") == "ResponseCompleted" for e in events)

    async def test_request_with_x_forwarded_for_header(self):
        """Extract remote address from x-forwarded-for header."""
        config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(self.mock_app, config=config)

        request = self._make_request(
            json_body={"model": "test"},
            headers=[(b"x-forwarded-for", b"192.168.1.1, 10.0.0.1")]
        )
        response = self._make_response(200)

        async def call_next(req):
            return response

        await middleware.dispatch(request, call_next)

        events = self.in_memory.get_events()
        request_event = next(e for e in events if e.get("event_type") == "RequestReceived")
        assert request_event["remote_addr"] == "192.168.1.1"

    async def test_request_with_x_real_ip_header(self):
        """Extract remote address from x-real-ip header."""
        config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(self.mock_app, config=config)

        request = self._make_request(
            json_body={"model": "test"},
            headers=[(b"x-real-ip", b"203.0.113.42")]
        )
        response = self._make_response(200)

        async def call_next(req):
            return response

        await middleware.dispatch(request, call_next)

        events = self.in_memory.get_events()
        request_event = next(e for e in events if e.get("event_type") == "RequestReceived")
        assert request_event["remote_addr"] == "203.0.113.42"

    async def test_request_without_client_info(self):
        """Handle request without client information."""
        config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(self.mock_app, config=config)

        # Create request without client
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [(b"content-type", b"application/json")],
            "query_string": b"",
            "client": None,
            "app": self.mock_app,
        }
        request = Request(scope)

        async def receive():
            return {"type": "http.request", "body": json.dumps({"model": "test"}).encode(), "more_body": False}
        request._receive = receive

        response = self._make_response(200)

        async def call_next(req):
            return response

        await middleware.dispatch(request, call_next)

        events = self.in_memory.get_events()
        request_event = next(e for e in events if e.get("event_type") == "RequestReceived")
        assert request_event["remote_addr"] == "unknown"

    async def test_streaming_response_without_usage(self):
        """Handle streaming response that doesn't contain usage."""
        config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(self.mock_app, config=config)

        request = self._make_request(json_body={"model": "test", "stream": True})

        # Create streaming response without usage
        async def stream_generator():
            yield b'data: {"choices": [{"delta": {"content": "test"}}]}\n\n'
            yield b'data: [DONE]\n\n'

        response = Response(content=b"", media_type="text/event-stream")
        response.body_iterator = stream_generator()

        async def call_next(req):
            return response

        result = await middleware.dispatch(request, call_next)

        # Should handle gracefully
        events = self.in_memory.get_events()
        completion_event = next(e for e in events if e.get("event_type") == "ResponseCompleted")
        assert completion_event["streaming"] is True

    async def test_response_without_body_attribute(self):
        """Handle response without body attribute."""
        config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(self.mock_app, config=config)

        request = self._make_request(json_body={"model": "test", "stream": False})

        # Create response without body attribute
        response = Response(content=b"test")
        delattr(response, "body")

        async def call_next(req):
            return response

        result = await middleware.dispatch(request, call_next)

        # Should handle gracefully
        events = self.in_memory.get_events()
        completion_event = next(e for e in events if e.get("event_type") == "ResponseCompleted")
        assert completion_event["missing_usage"] is True

    async def test_response_with_non_json_body(self):
        """Handle response with non-JSON body."""
        config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory],
            reasoning_policy=NoOpReasoningPolicy(),
        )
        middleware = TelemetryMiddleware(self.mock_app, config=config)

        request = self._make_request(json_body={"model": "test", "stream": False})

        response = Response(content=b"not json", media_type="text/plain")
        response.body = b"not json"

        async def call_next(req):
            return response

        result = await middleware.dispatch(request, call_next)

        events = self.in_memory.get_events()
        completion_event = next(e for e in events if e.get("event_type") == "ResponseCompleted")
        assert completion_event["parse_error"] is True


class EnabledToggle:
    def enabled(self, request):
        return True
