#!/usr/bin/env python3
from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi import Request

from src.middleware.telemetry.request_context import (
    NoOpReasoningPolicy,
    apply_reasoning_policy,
)


class TestRequestContext:
    """Test reasoning policy application and fallback."""

    def _make_request(self, method="POST", path="/v1/chat/completions", json_body=None):
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [(b"content-type", b"application/json")],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "app": SimpleNamespace(),
        }
        req = Request(scope)
        if json_body:
            async def receive():
                return {"type": "http.request", "body": json.dumps(json_body).encode(), "more_body": False}
            req._receive = receive
        return req

    def test_noop_policy_returns_unchanged_request(self):
        """NoOpReasoningPolicy should return request unchanged."""
        policy = NoOpReasoningPolicy()
        request = self._make_request()

        result_request, metadata = policy.apply(request)

        assert result_request is request
        assert metadata == {}

    def test_apply_reasoning_policy_with_working_policy(self):
        """apply_reasoning_policy should use provided policy."""
        class CustomPolicy:
            def apply(self, request):
                return request, {"custom": "metadata"}

        policy = CustomPolicy()
        request = self._make_request()

        result_request, metadata = apply_reasoning_policy(policy, request)

        assert result_request is request
        assert metadata == {"custom": "metadata"}

    def test_apply_reasoning_policy_fallback_on_exception(self):
        """apply_reasoning_policy should fallback to no-op on exception."""
        class FailingPolicy:
            def apply(self, request):
                raise RuntimeError("Policy failure")

        policy = FailingPolicy()
        request = self._make_request()

        # Should not raise, should fallback to no-op
        result_request, metadata = apply_reasoning_policy(policy, request)

        assert result_request is request
        assert metadata == {}

    def test_apply_reasoning_policy_handles_various_exceptions(self):
        """apply_reasoning_policy should handle different exception types."""
        class PolicyWithTypeError:
            def apply(self, request):
                raise TypeError("Type error")

        policy = PolicyWithTypeError()
        request = self._make_request()

        result_request, metadata = apply_reasoning_policy(policy, request)

        assert result_request is request
        assert metadata == {}
