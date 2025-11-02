#!/usr/bin/env python3
"""Unit tests for telemetry middleware - request logging and monitoring."""

from __future__ import annotations

import json
import logging
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request, Response
from src.config.models import ModelSpec
from src.telemetry.middleware import TelemetryMiddleware
from src.telemetry.alias_lookup import create_alias_lookup
from src.telemetry.instrumentation import instrument_proxy_logging


class TestAliasLookup:
    """Test alias→upstream lookup functionality."""

    def test_create_alias_lookup_basic(self):
        """Test basic alias lookup creation."""
        model_specs = [
            ModelSpec(
                key="gpt4",
                alias="gpt-4",
                upstream_model="gpt-4",
                upstream_base="https://api.openai.com/v1"
            ),
            ModelSpec(
                key="claude",
                alias="claude-3",
                upstream_model="claude-3-sonnet",
                upstream_base="https://api.anthropic.com"
            )
        ]

        lookup = create_alias_lookup(model_specs)

        assert lookup["gpt-4"] == "openai/gpt-4"
        assert lookup["claude-3"] == "openai/claude-3-sonnet"

    def test_create_alias_lookup_with_already_prefixed(self):
        """Test alias lookup when upstream_model already has openai/ prefix."""
        model_specs = [
            ModelSpec(
                key="prefixed",
                alias="gpt-4-turbo",
                upstream_model="openai/gpt-4-turbo"
            )
        ]

        lookup = create_alias_lookup(model_specs)
        assert lookup["gpt-4-turbo"] == "openai/gpt-4-turbo"

    def test_create_alias_lookup_empty(self):
        """Test alias lookup with empty model specs."""
        lookup = create_alias_lookup([])
        assert lookup == {}

    def test_create_alias_lookup_duplicate_aliases(self):
        """Test alias lookup with duplicate aliases - last one wins."""
        model_specs = [
            ModelSpec(
                key="first",
                alias="duplicate",
                upstream_model="first-model"
            ),
            ModelSpec(
                key="second",
                alias="duplicate",
                upstream_model="second-model"
            )
        ]

        lookup = create_alias_lookup(model_specs)
        assert lookup["duplicate"] == "openai/second-model"


class TestTelemetryMiddleware:
    """Test telemetry middleware functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.model_specs = [
            ModelSpec(
                key="test",
                alias="test-model",
                upstream_model="gpt-4"
            )
        ]
        self.alias_lookup = create_alias_lookup(self.model_specs)

        # Mock FastAPI app
        self.mock_app = MagicMock()
        self.mock_app.state = SimpleNamespace(litellm_telemetry_alias_lookup=self.alias_lookup)

        # Set up logger capture BEFORE creating middleware
        self.log_records = []
        self.test_handler = logging.Handler()
        self.test_handler.emit = lambda record: self.log_records.append(record)

        self.logger = logging.getLogger("litellm_launcher.telemetry")
        self.logger.addHandler(self.test_handler)
        self.logger.setLevel(logging.INFO)

        # Create middleware (will use the logger we just configured)
        self.middleware = TelemetryMiddleware(
            app=self.mock_app,
            alias_lookup=self.alias_lookup
        )

    def teardown_method(self):
        """Clean up test environment."""
        self.logger.removeHandler(self.test_handler)

    def create_mock_request(self, method="POST", path="/v1/chat/completions",
                            headers=None, json_body=None) -> Request:
        """Create a mock FastAPI Request."""
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers or [],
            "query_string": b"",
            "client": ("192.168.1.100", 12345),
            "app": self.mock_app,
        }

        request = Request(scope)
        if json_body:
            request._json = json_body
        return request

    def create_mock_response(self, status_code=200, json_body=None,
                             headers=None) -> Response:
        """Create a mock FastAPI Response."""
        content = json.dumps(json_body or {}).encode()
        response = Response(
            content=content,
            status_code=status_code,
            headers=headers or {"content-type": "application/json"}
        )
        # Set body attribute for telemetry middleware
        response.body = content
        return response

    def test_non_streaming_success_with_usage(self):
        """Test successful non-streaming request with usage data."""
        # Create request
        request = self.create_mock_request(
            json_body={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False
            }
        )

        # Create response with usage
        response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "test-model",
            "choices": [],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
                "output_token_details": {
                    "reasoning_tokens": 5
                }
            }
        }

        response = self.create_mock_response(200, response_data)

        # Mock the call_next to return our response
        async def mock_call_next(req):
            return response

        with patch('time.perf_counter') as mock_time:
            mock_time.side_effect = [0.0, 0.150]  # Start time, end time (150ms)

            # Execute middleware
            import asyncio
            asyncio.run(self.middleware.dispatch(request, mock_call_next))

        # Verify log was emitted
        assert len(self.log_records) == 1
        log_record = self.log_records[0]
        assert log_record.levelno == logging.INFO

        # Parse logged JSON
        logged_data = json.loads(log_record.getMessage())

        # Verify all required fields (filtered per PRD specification)
        assert logged_data["status_code"] == 200
        assert logged_data["duration_ms"] == 150.0
        assert logged_data["streaming"] is False
        assert logged_data["upstream_model"] == "openai/gpt-4"
        assert logged_data["prompt_tokens"] == 10
        assert logged_data["completion_tokens"] == 20
        assert logged_data["reasoning_tokens"] == 5
        assert logged_data["total_tokens"] == 30
        assert logged_data["error_type"] is None
        assert logged_data["error_message"] is None
        # Verify filtered fields are NOT present per specification
        assert "event" not in logged_data
        assert "path" not in logged_data
        assert "method" not in logged_data
        assert "request_id" not in logged_data
        assert "model_alias" not in logged_data
        assert "timestamp" not in logged_data
        assert "remote_addr" not in logged_data

    def test_parse_usage_fallback_sums_tokens(self):
        """Fallback path should compute total tokens when missing."""
        usage = self.middleware._parse_usage_from_response({
            "usage": {"input_tokens": 4, "output_tokens": 6}
        })
        assert usage["prompt_tokens"] == 4
        assert usage["completion_tokens"] == 6
        assert usage["total_tokens"] == 10

    def test_get_remote_addr_header_fallbacks(self):
        """_get_remote_addr should prefer forwarded headers when client missing."""
        request = self.create_mock_request(headers=[(b"x-forwarded-for", b"10.0.0.1")])
        request.scope["client"] = None  # type: ignore[attr-defined]
        assert self.middleware._get_remote_addr(request) == "10.0.0.1"

        request = self.create_mock_request(headers=[(b"x-real-ip", b"172.16.0.5")])
        request.scope["client"] = None  # type: ignore[attr-defined]
        assert self.middleware._get_remote_addr(request) == "172.16.0.5"

        request = self.create_mock_request(headers=[])
        request.scope["client"] = None  # type: ignore[attr-defined]
        assert self.middleware._get_remote_addr(request) == "unknown"

    def test_non_post_request_passthrough(self):
        """Requests to other endpoints should bypass telemetry."""
        request = self.create_mock_request(method="GET", path="/v1/chat/completions")
        response = self.create_mock_response(204, {})

        async def mock_call_next(req):
            return response

        import asyncio
        result = asyncio.run(self.middleware.dispatch(request, mock_call_next))

        assert result is response
        assert self.log_records == []

    def test_dispatch_handles_json_parse_error(self):
        """Middleware should tolerate JSON parsing failures."""
        request = self.create_mock_request()

        async def failing_json():
            raise ValueError("bad json")

        request.json = failing_json  # type: ignore[assignment]

        response = self.create_mock_response(200, {"choices": []})

        async def mock_call_next(req):
            return response

        import asyncio
        result = asyncio.run(self.middleware.dispatch(request, mock_call_next))

        assert result is response
        assert len(self.log_records) == 1

        logged_data = json.loads(self.log_records[0].getMessage())
        assert logged_data["upstream_model"] == "openai/unknown"

    def test_non_streaming_success_missing_usage(self):
        """Test successful non-streaming request with missing usage data."""
        request = self.create_mock_request(
            json_body={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False
            }
        )

        # Response without usage field
        response_data = {
            "id": "chatcmpl-456",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "test-model",
            "choices": []
            # No usage field
        }

        response = self.create_mock_response(200, response_data)

        async def mock_call_next(req):
            return response

        with patch('time.perf_counter') as mock_time:
            mock_time.side_effect = [0.0, 0.100]

            import asyncio
            asyncio.run(self.middleware.dispatch(request, mock_call_next))

        # Verify log was emitted with missing_usage flag
        assert len(self.log_records) == 1
        logged_data = json.loads(self.log_records[0].getMessage())

        assert logged_data["missing_usage"] is True
        assert logged_data["prompt_tokens"] is None
        assert logged_data["completion_tokens"] is None
        assert logged_data["total_tokens"] is None
        # Verify filtered fields are NOT present per specification
        assert "event" not in logged_data
        assert "path" not in logged_data
        assert "method" not in logged_data
        assert "request_id" not in logged_data
        assert "model_alias" not in logged_data
        assert "timestamp" not in logged_data
        assert "remote_addr" not in logged_data

    def test_streaming_success_with_usage(self):
        """Test successful streaming request with usage in final chunk."""
        request = self.create_mock_request(
            json_body={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True
            }
        )

        # Mock streaming response generator
        async def mock_stream_generator():
            # Initial chunks
            yield b'data: {"choices": [{"delta": {"content": "Hi"}}}\n\n'
            yield b'data: {"choices": [{"delta": {"content": " there"}}\n\n'
            # Final chunk with usage
            yield (
                b'data: {"usage": {"prompt_tokens": 15, "completion_tokens": 25, '
                b'"total_tokens": 40, "output_token_details": {"reasoning_tokens": 8}}}\n\n'
            )
            yield b'data: [DONE]\n\n'

        async def mock_call_next(req):
            return mock_stream_generator()

        with patch('time.perf_counter') as mock_time:
            mock_time.side_effect = [0.0, 0.200]  # 200ms streaming duration

            import asyncio
            asyncio.run(self.middleware.dispatch(request, mock_call_next))

        # Verify log was emitted after streaming completion
        assert len(self.log_records) == 1
        logged_data = json.loads(self.log_records[0].getMessage())

        assert logged_data["streaming"] is True
        assert logged_data["duration_ms"] == 200.0
        assert logged_data["prompt_tokens"] == 15
        assert logged_data["completion_tokens"] == 25
        assert logged_data["reasoning_tokens"] == 8
        assert logged_data["total_tokens"] == 40
        # Verify filtered fields are NOT present per specification
        assert "event" not in logged_data
        assert "path" not in logged_data
        assert "method" not in logged_data
        assert "request_id" not in logged_data
        assert "model_alias" not in logged_data
        assert "timestamp" not in logged_data
        assert "remote_addr" not in logged_data

    def test_extract_streaming_usage_json_fallback(self):
        """Streaming usage parser should fall back to JSON when SSE parsing fails."""
        class AsyncIterResponse:
            def __init__(self, chunks):
                self._chunks = chunks

            def __aiter__(self):
                async def generator():
                    for chunk in self._chunks:
                        yield chunk
                return generator()

        response = AsyncIterResponse([b'{"usage": {"input_tokens": 2, "output_tokens": 3}}'])

        import asyncio
        reconstructed, usage = asyncio.run(self.middleware._extract_streaming_usage(response))

        assert hasattr(reconstructed, "__aiter__")
        assert usage["prompt_tokens"] == 2
        assert usage["completion_tokens"] == 3
        assert usage["total_tokens"] == 5

    def test_extract_streaming_usage_body_iterator(self):
        """StreamingResponse-style body_iterator should be parsed and restored."""
        class BodyIteratorResponse:
            def __init__(self, chunks):
                async def iterator():
                    for chunk in chunks:
                        yield chunk
                self.body_iterator = iterator()

        response = BodyIteratorResponse([
            b'data: {"id": "abc", "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}\n\n',
            b'data: [DONE]\n\n',
        ])

        import asyncio
        reconstructed, usage = asyncio.run(self.middleware._extract_streaming_usage(response))

        assert reconstructed is response
        assert usage["prompt_tokens"] == 1
        assert usage["completion_tokens"] == 2
        assert usage["total_tokens"] == 3

    def test_error_response_with_exception(self):
        """Test error response with exception details."""
        request = self.create_mock_request(
            json_body={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )

        async def mock_call_next_with_error(req):
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        with patch('time.perf_counter') as mock_time:
            mock_time.side_effect = [0.0, 0.050]

            import asyncio
            with pytest.raises(Exception):  # Exception should be re-raised
                asyncio.run(self.middleware.dispatch(request, mock_call_next_with_error))

        # Verify error log was emitted
        assert len(self.log_records) == 1
        logged_data = json.loads(self.log_records[0].getMessage())

        assert logged_data["status_code"] == 429
        assert logged_data["error_type"] == "HTTPException"
        assert "Rate limit exceeded" in logged_data["error_message"]
        assert logged_data["prompt_tokens"] is None
        assert logged_data["completion_tokens"] is None
        # Verify filtered fields are NOT present per specification
        assert "event" not in logged_data
        assert "path" not in logged_data
        assert "method" not in logged_data
        assert "request_id" not in logged_data
        assert "model_alias" not in logged_data
        assert "timestamp" not in logged_data
        assert "remote_addr" not in logged_data

    def test_request_with_client_request_id(self):
        """Test request includes X-Request-ID header."""
        request = self.create_mock_request(
            headers=[(b"x-request-id", b"client-req-123")],
            json_body={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )

        response_data = {
            "id": "chatcmpl-789",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "test-model",
            "choices": [],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
        }

        response = self.create_mock_response(200, response_data)

        async def mock_call_next(req):
            return response

        with patch('time.perf_counter') as mock_time:
            mock_time.side_effect = [0.0, 0.080]

            import asyncio
            asyncio.run(self.middleware.dispatch(request, mock_call_next))

        # Verify client_request_id is included
        assert len(self.log_records) == 1
        logged_data = json.loads(self.log_records[0].getMessage())
        assert logged_data["client_request_id"] == "client-req-123"
        # Verify filtered fields are NOT present per specification
        assert "event" not in logged_data
        assert "path" not in logged_data
        assert "method" not in logged_data
        assert "request_id" not in logged_data
        assert "model_alias" not in logged_data
        assert "timestamp" not in logged_data
        assert "remote_addr" not in logged_data

    def test_unknown_model_alias(self):
        """Test request with unknown model alias."""
        request = self.create_mock_request(
            json_body={
                "model": "unknown-model",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )

        response_data = {
            "id": "chatcmpl-999",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "unknown-model",
            "choices": [],
            "usage": {"prompt_tokens": 8, "completion_tokens": 12, "total_tokens": 20}
        }

        response = self.create_mock_response(200, response_data)

        async def mock_call_next(req):
            return response

        with patch('time.perf_counter') as mock_time:
            mock_time.side_effect = [0.0, 0.060]

            import asyncio
            asyncio.run(self.middleware.dispatch(request, mock_call_next))

        # Verify upstream_model defaults to alias when unknown
        assert len(self.log_records) == 1
        logged_data = json.loads(self.log_records[0].getMessage())
        assert logged_data["upstream_model"] == "openai/unknown-model"
        # Verify filtered fields are NOT present per specification
        assert "event" not in logged_data
        assert "path" not in logged_data
        assert "method" not in logged_data
        assert "request_id" not in logged_data
        assert "model_alias" not in logged_data
        assert "timestamp" not in logged_data
        assert "remote_addr" not in logged_data

    def test_parse_error_resilience(self):
        """Test middleware resilience to JSON parsing errors."""
        request = self.create_mock_request(
            json_body={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )

        # Response with invalid JSON that causes parsing error
        response = Response(
            content=b"invalid json response",
            status_code=200,
            headers={"content-type": "application/json"}
        )

        async def mock_call_next(req):
            return response

        with patch('time.perf_counter') as mock_time:
            mock_time.side_effect = [0.0, 0.040]

            import asyncio
            asyncio.run(self.middleware.dispatch(request, mock_call_next))

        # Verify parse error is handled gracefully
        assert len(self.log_records) == 1
        logged_data = json.loads(self.log_records[0].getMessage())
        assert logged_data["parse_error"] is True
        # Should still have basic fields
        assert logged_data["status_code"] == 200
        assert logged_data["duration_ms"] == 40.0
        # Verify filtered fields are NOT present per specification
        assert "event" not in logged_data
        assert "path" not in logged_data
        assert "method" not in logged_data
        assert "request_id" not in logged_data
        assert "model_alias" not in logged_data
        assert "timestamp" not in logged_data
        assert "remote_addr" not in logged_data


class TestInstrumentProxyLogging:
    """Test proxy logging instrumentation function."""

    @staticmethod
    def _setup_stub_app():
        mock_app = MagicMock()
        mock_app.state = SimpleNamespace()
        mock_app.add_middleware = MagicMock()

        proxy_server_module = ModuleType("proxy_server")
        proxy_server_module.app = mock_app

        proxy_module = ModuleType("proxy")
        proxy_module.proxy_server = proxy_server_module

        litellm_module = ModuleType("litellm")
        litellm_module.proxy = proxy_module

        module_map = {
            "litellm": litellm_module,
            "litellm.proxy": proxy_module,
            "litellm.proxy.proxy_server": proxy_server_module,
        }

        return mock_app, module_map

    def test_instrument_proxy_logging_registers_middleware(self):
        """Test that instrument_proxy_logging properly registers middleware."""
        # Create mock model specs
        model_specs = [
            ModelSpec(
                key="test",
                alias="test-model",
                upstream_model="gpt-4"
            )
        ]

        mock_app, module_map = self._setup_stub_app()

        with patch.dict(sys.modules, module_map, clear=False):
            instrument_proxy_logging(model_specs)

        # Verify middleware was added to app
        mock_app.add_middleware.assert_called_once()
        args, kwargs = mock_app.add_middleware.call_args
        assert args[0] is TelemetryMiddleware
        assert kwargs["alias_lookup"]["test-model"] == "openai/gpt-4"
        assert mock_app.state.litellm_telemetry_alias_lookup == kwargs["alias_lookup"]
        assert mock_app.state._litellm_telemetry_installed is True

    def test_instrument_proxy_logging_is_idempotent(self):
        """Telemetry middleware should only register once."""
        model_specs = []
        mock_app, module_map = self._setup_stub_app()

        with patch.dict(sys.modules, module_map, clear=False):
            instrument_proxy_logging(model_specs)
            instrument_proxy_logging(model_specs)

        mock_app.add_middleware.assert_called_once()

    @patch('src.telemetry.logging.getLogger')
    def test_instrument_proxy_logging_logger_setup(self, mock_get_logger):
        """Test that logger is properly configured during instrumentation."""
        model_specs = []

        mock_app, module_map = self._setup_stub_app()
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch.dict(sys.modules, module_map, clear=False):
            instrument_proxy_logging(model_specs)

        # Verify our logger was configured (ignore other logger calls from imports)
        mock_get_logger.assert_called_with("litellm_launcher.telemetry")
        mock_logger.setLevel.assert_called_with(logging.INFO)
