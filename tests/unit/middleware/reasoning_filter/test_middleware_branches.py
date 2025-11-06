#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
from types import SimpleNamespace

from fastapi import Request

from src.middleware.reasoning_filter.middleware import ReasoningFilterMiddleware


class TestReasoningFilterBranches:
    """Test uncovered branches in ReasoningFilterMiddleware."""

    def setup_method(self):
        self.log_records = []
        handler = logging.Handler()
        handler.setLevel(logging.DEBUG)
        handler.emit = lambda rec: self.log_records.append(rec)
        self.logger = logging.getLogger("litellm_launcher.filter")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        
        self.mock_app = SimpleNamespace()
        self.middleware = ReasoningFilterMiddleware(self.mock_app)

    def teardown_method(self):
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

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

    async def test_filter_with_x_request_id_header(self):
        """Filter should log client_request_id when present."""
        request = self._make_request(
            json_body={"model": "test", "reasoning": "high"},
            headers=[(b"x-request-id", b"req-123")]
        )
        
        response_called = False
        
        async def call_next(req):
            nonlocal response_called
            response_called = True
            from fastapi import Response
            return Response(content=b"{}")
        
        await self.middleware.dispatch(request, call_next)
        
        assert response_called
        # Should log with client_request_id
        assert len(self.log_records) == 1
        log_msg = json.loads(self.log_records[0].getMessage())
        assert log_msg["client_request_id"] == "req-123"
        assert log_msg["dropped_param"] == "reasoning"

    async def test_filter_empty_body(self):
        """Filter should handle empty request body."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [(b"content-type", b"application/json")],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "app": self.mock_app,
        }
        request = Request(scope)
        
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        request._receive = receive
        
        response_called = False
        
        async def call_next(req):
            nonlocal response_called
            response_called = True
            from fastapi import Response
            return Response(content=b"{}")
        
        await self.middleware.dispatch(request, call_next)
        
        assert response_called
        # Should not log anything
        assert len(self.log_records) == 0

    async def test_filter_invalid_json_body(self):
        """Filter should handle invalid JSON gracefully."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [(b"content-type", b"application/json")],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "app": self.mock_app,
        }
        request = Request(scope)
        
        async def receive():
            return {"type": "http.request", "body": b"not valid json", "more_body": False}
        request._receive = receive
        
        response_called = False
        
        async def call_next(req):
            nonlocal response_called
            response_called = True
            from fastapi import Response
            return Response(content=b"{}")
        
        await self.middleware.dispatch(request, call_next)
        
        assert response_called
        # Should not log anything
        assert len(self.log_records) == 0

    async def test_filter_non_dict_payload(self):
        """Filter should handle non-dict JSON payloads."""
        request = self._make_request(method="POST", path="/v1/chat/completions")
        
        async def receive():
            return {"type": "http.request", "body": b'["array", "payload"]', "more_body": False}
        request._receive = receive
        
        response_called = False
        
        async def call_next(req):
            nonlocal response_called
            response_called = True
            from fastapi import Response
            return Response(content=b"{}")
        
        await self.middleware.dispatch(request, call_next)
        
        assert response_called
        # Should not log anything (no reasoning to drop)
        assert len(self.log_records) == 0

    async def test_filter_non_openai_path(self):
        """Filter should not process non-OpenAI paths."""
        request = self._make_request(
            method="POST",
            path="/custom/endpoint",
            json_body={"model": "test", "reasoning": "high"}
        )
        
        response_called = False
        
        async def call_next(req):
            nonlocal response_called
            response_called = True
            from fastapi import Response
            return Response(content=b"{}")
        
        await self.middleware.dispatch(request, call_next)
        
        assert response_called
        # Should not log anything (path not in filter list)
        assert len(self.log_records) == 0

    async def test_filter_get_request(self):
        """Filter should not process GET requests."""
        request = self._make_request(method="GET", path="/v1/chat/completions")
        
        response_called = False
        
        async def call_next(req):
            nonlocal response_called
            response_called = True
            from fastapi import Response
            return Response(content=b"{}")
        
        await self.middleware.dispatch(request, call_next)
        
        assert response_called
        # Should not log anything (not POST)
        assert len(self.log_records) == 0
