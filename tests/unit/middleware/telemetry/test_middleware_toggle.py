#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Protocol

from fastapi import Request, Response

# Target new package per PRD
from src.middleware.telemetry.middleware import TelemetryMiddleware
from src.middleware.telemetry.config import TelemetryConfig


class TelemetryToggle(Protocol):
    def enabled(self, request: Request) -> bool: ...


class NoOpReasoningPolicy(Protocol):
    def apply(self, request: Request): ...


class InMemorySink:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


class TestTelemetryTogglePassThrough:
    def setup_method(self):
        self.log_records = []
        handler = logging.Handler()
        handler.setLevel(logging.DEBUG)
        handler.emit = lambda record: self.log_records.append(record)
        logging.getLogger("litellm_launcher.telemetry").addHandler(handler)

        self.mock_app = SimpleNamespace(state=SimpleNamespace(litellm_telemetry_alias_lookup={}))

        class DisabledToggle:
            def enabled(self, request: Request) -> bool:
                return False

        self.disabled_toggle = DisabledToggle()
        self.sink = InMemorySink()

        class NoOpPolicy:
            def apply(self, request: Request):
                return request, {"policy": "noop"}

        self.policy = NoOpPolicy()

        self.config = TelemetryConfig(
            toggle=self.disabled_toggle,
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.sink],
            reasoning_policy=self.policy,
        )

        self.middleware = TelemetryMiddleware(app=self.mock_app, config=self.config)

    def teardown_method(self):
        logger = logging.getLogger("litellm_launcher.telemetry")
        for h in list(logger.handlers):
            if h.__class__ is logging.Handler:
                logger.removeHandler(h)

    def _make_request(self, method="POST", path="/v1/chat/completions", body: bytes = b"") -> Request:
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "app": self.mock_app,
        }
        req = Request(scope)

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}
        req._receive = receive
        return req

    def test_toggle_false_pass_through(self):
        request = self._make_request(body=b'{"model":"x","messages":[],"stream":false}')
        response = Response(content=b'{"ok":true}', media_type="application/json")
        response.body = response.body if hasattr(response, "body") else response.body

        async def call_next(req: Request):
            return response

        result = asyncio.run(self.middleware.dispatch(request, call_next))

        assert result is response, "Middleware must pass-through when toggle is disabled"
        assert len(self.sink.events) == 0, "No events should be emitted when toggle=false"
        assert len(self.log_records) == 0, "No logger output expected when toggle=false"
