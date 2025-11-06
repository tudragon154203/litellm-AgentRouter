#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import pytest
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import Request, Response

from src.middleware.telemetry.middleware import TelemetryMiddleware
from src.middleware.telemetry.config import TelemetryConfig
from src.middleware.telemetry.sinks.inmemory import InMemorySink
from src.middleware.telemetry.sinks.logger import LoggerSink
from src.middleware.telemetry.request_context import NoOpReasoningPolicy


class TestJSONFlow:
    """Test non-streaming request with usage extraction and multi-sink fan-out."""

    def setup_method(self):
        self.log_records = []
        # Use same logger name as LoggerSink to capture its logs
        handler = logging.Handler()
        handler.setLevel(logging.DEBUG)
        handler.emit = lambda rec: self.log_records.append(rec)
        self.logger = logging.getLogger("litellm.telemetry")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        self.mock_app = SimpleNamespace(state=SimpleNamespace(litellm_telemetry_alias_lookup={}))
        self.in_memory = InMemorySink()
        self.logger_sink = LoggerSink("litellm.telemetry")
        self.config = TelemetryConfig(
            toggle=EnabledToggle(),
            alias_resolver=lambda alias: f"openai/{alias}",
            sinks=[self.in_memory, self.logger_sink],
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

    def _make_response(self, status_code=200, json_body=None):
        content = (json.dumps(json_body) if json_body else "{}").encode()
        resp = Response(content=content, media_type="application/json")
        resp.status_code = status_code
        resp.body = content
        return resp

    async def test_json_success_with_usage_and_fanout(self):
        request = self._make_request(json_body={"model": "gpt-4", "stream": False})
        response = self._make_response(200, {
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        })

        async def call_next(req):
            return response

        with patch("time.perf_counter") as mock_time:
            mock_time.side_effect = [0.0, 0.150]
            result = await self.middleware.dispatch(request, call_next)

        assert result is response
        # InMemorySink should capture an event (implementation may emit one event or two; we only verify one non-empty)
        assert any(event for event in self.in_memory.get_events() if event), "InMemorySink should have captured an event"
        # LoggerSink should emit a JSON line via INFO
        assert len(self.log_records) == 1
        log_record = self.log_records[0]
        assert log_record.levelno == logging.INFO
        logged = log_record.getMessage()
        assert "prompt_tokens" in logged
        assert "completion_tokens" in logged


class EnabledToggle:
    def enabled(self, request):
        return True
