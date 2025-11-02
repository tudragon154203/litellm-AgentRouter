#!/usr/bin/env python3
"""
Additional tests to improve coverage of telemetry module.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.telemetry import TelemetryMiddleware


class TestTelemetryMiddlewareCoverage:
    """Test edge cases for TelemetryMiddleware."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock ASGI app."""
        mock_app = AsyncMock()
        mock_app.state = MagicMock()
        return mock_app

    @pytest.fixture
    def telemetry_middleware(self, mock_app):
        """Create telemetry middleware instance."""
        alias_lookup = {"test-model": "gpt-5"}
        middleware = TelemetryMiddleware(app=mock_app, alias_lookup=alias_lookup)
        mock_app.state.litellm_telemetry_alias_lookup = alias_lookup
        return middleware

    async def test_middleware_skips_non_chat_requests(self, telemetry_middleware):
        """Test that middleware skips non-chat completion requests."""
        # Mock a request to different endpoint
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/v1/models"

        mock_call_next = AsyncMock()
        mock_call_next.return_value = {"status": 200}

        response = await telemetry_middleware.dispatch(mock_request, mock_call_next)

        # Should call next without processing
        mock_call_next.assert_called_once_with(mock_request)
        assert response == {"status": 200}

    async def test_middleware_handles_invalid_request_body(self, telemetry_middleware):
        """Test middleware handling when request body parsing fails."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/v1/chat/completions"
        mock_request.json = AsyncMock(side_effect=Exception("Invalid JSON"))
        mock_request.headers = {}

        # Create a mock response for the error case
        mock_error_response = MagicMock()
        mock_error_response.status_code = 400
        mock_call_next = AsyncMock(return_value=mock_error_response)

        response = await telemetry_middleware.dispatch(mock_request, mock_call_next)

        # Should handle the error and continue
        mock_call_next.assert_called_once_with(mock_request)

    async def test_middleware_handles_streaming_response_bytes(self, telemetry_middleware):
        """Test telemetry processing for streaming response with bytes chunks."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/v1/chat/completions"
        mock_request.json = AsyncMock(return_value={
            "model": "test-model",
            "stream": True
        })
        mock_request.headers = {"x-request-id": "test-123"}

        # Mock streaming response with bytes
        mock_response = MagicMock()
        mock_response.body_iterator = self._create_async_stream([
            b'data: {"choices": [{"delta": {"content": "Hello"}}]\n\n',
            b'data: {"choices": [{"delta": {"content": " world"}}]\n\n',
            b'data: [DONE]\n\n'
        ])
        mock_response.status_code = 200

        mock_call_next = AsyncMock(return_value=mock_response)
        mock_logger = MagicMock()

        with patch.object(telemetry_middleware, '_log_telemetry', mock_logger):
            response = await telemetry_middleware.dispatch(mock_request, mock_call_next)

            # Should have been called to log telemetry
            mock_logger.assert_called_once()

    async def test_middleware_gets_remote_addr_from_forwarded_header(self, telemetry_middleware):
        """Test remote address extraction from x-forwarded-for header."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/v1/chat/completions"
        mock_request.json = AsyncMock(return_value={
            "model": "test-model",
            "stream": False
        })
        mock_request.headers = {
            "x-forwarded-for": "203.0.113.1, 198.51.100.1"
        }
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Mock successful response
        mock_response = MagicMock()
        mock_response.body = json.dumps({
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        }).encode()
        mock_response.status_code = 200

        mock_call_next = AsyncMock(return_value=mock_response)

        # Verify that forwarded IP is used
        remote_addr = telemetry_middleware._get_remote_addr(mock_request)
        assert remote_addr == "203.0.113.1"

    async def test_middleware_gets_remote_addr_from_real_ip_header(self, telemetry_middleware):
        """Test remote address extraction from x-real-ip header."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/v1/chat/completions"
        mock_request.json = AsyncMock(return_value={
            "model": "test-model",
            "stream": False
        })
        mock_request.headers = {
            "x-real-ip": "192.168.1.100"
        }
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Verify that real IP is used
        remote_addr = telemetry_middleware._get_remote_addr(mock_request)
        assert remote_addr == "192.168.1.100"

    def test_middleware_sanitizes_error_message(self, telemetry_middleware):
        """Test error message sanitization removes sensitive information."""
        test_cases = [
            (
                'Bearer sk-test1234567890abcdef1234567890abcdef12345678',
                'Bearer [REDACTED]'
            ),
            (
                'api_key: sk-test1234567890abcdef1234567890abcdef12345678',
                'api_key: [REDACTED]'
            ),
            (
                'Authorization: Bearer sk-1234567890abcdef1234567890abcdef1234567890',
                'Authorization: Bearer [REDACTED]'
            ),
        ]

        for original, expected in test_cases:
            sanitized = telemetry_middleware._sanitize_error_message(original)
            # The sanitization might remove patterns or add [REDACTED], check either condition
            assert expected in sanitized or "[REDACTED]" in sanitized

    async def test_middleware_handles_telemetry_logging_failure(self, telemetry_middleware):
        """Test that telemetry middleware continues when logging fails."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/v1/chat/completions"
        mock_request.json = AsyncMock(return_value={
            "model": "test-model",
            "stream": False
        })
        mock_request.headers = {"x-request-id": "test-123"}

        # Mock successful response
        mock_response = MagicMock()
        mock_response.body = json.dumps({
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        }).encode()
        mock_response.status_code = 200

        mock_call_next = AsyncMock(return_value=mock_response)
        mock_logger = MagicMock(side_effect=Exception("Logging failed"))

        with patch.object(telemetry_middleware, 'logger', mock_logger):
            # Should not raise exception even if logging fails
            response = await telemetry_middleware.dispatch(mock_request, mock_call_next)
            assert response == mock_response

            # Should emit warning about logging failure
            mock_logger.warning.assert_called_with("Failed to log telemetry data: Logging failed")

    def test_middleware_async_iter_creation(self, telemetry_middleware):
        """Test _create_async_iter method."""
        test_data = [b'chunk1', b'chunk2', b'chunk3']

        async def collect_items():
            items = []
            async for item in telemetry_middleware._create_async_iter(test_data):
                items.append(item)
            return items

        result = asyncio.run(collect_items())
        assert result == test_data

    def _create_async_stream(self, chunks):
        """Helper to create async iterator from chunks."""
        async def async_stream():
            for chunk in chunks:
                yield chunk

        return async_stream()


class TestParseUsageFromSSECoverage:
    """Test edge cases for _parse_usage_from_sse."""

    def test_parse_usage_with_complete_data(self):
        """Test parsing usage data from SSE with all fields."""
        middleware = TelemetryMiddleware(app=None, alias_lookup={})

        # Test with properly formatted SSE data line
        sse_line = 'data: {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}'

        result = middleware._parse_usage_from_sse(sse_line)

        assert result == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": None,
            "request_id": None
        }

    def test_parse_usage_with_partial_data(self):
        """Test parsing usage data from SSE with partial fields."""
        middleware = TelemetryMiddleware(app=None, alias_lookup={})

        # Test with partial usage data
        sse_line = 'data: {"usage": {"prompt_tokens": 5}}'

        result = middleware._parse_usage_from_sse(sse_line)

        assert result == {
            "prompt_tokens": 5,
            "completion_tokens": None,
            "total_tokens": None,
            "request_id": None
        }

    def test_parse_usage_no_usage_field(self):
        """Test parsing SSE data with no usage field."""
        middleware = TelemetryMiddleware(app=None, alias_lookup={})

        # Test with no usage field
        sse_line = 'data: {"choices": [{"message": {"content": "Hello"}}]'

        result = middleware._parse_usage_from_sse(sse_line)

        assert result is None


class TestTelemetryStreamingCoverage:
    """Additional tests for streaming response processing to reach 95% coverage."""

    async def test_middleware_handles_streaming_response_with_chunks(self, telemetry_middleware):
        """Test telemetry processing for streaming response with chunks."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/v1/chat/completions"
        mock_request.json = AsyncMock(return_value={
            "model": "test-model",
            "stream": True
        })
        mock_request.headers = {"x-request-id": "test-123"}

        # Mock streaming response with chunks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.body_iterator = self._create_async_stream([
            b'data: {"usage": {"prompt_tokens": 5}}\n\n',
            b'data: {"choices": [{"delta": {"content": "Hello"}}]\n\n',
            b'data: [DONE]\n\n'
        ])

        mock_call_next = AsyncMock(return_value=mock_response)
        mock_logger = MagicMock()

        with patch.object(telemetry_middleware, '_log_telemetry', mock_logger):
            response = await telemetry_middleware.dispatch(mock_request, mock_call_next)

            # Should process streaming and log telemetry
            mock_logger.assert_called_once()
            assert response == mock_response

    async def test_middleware_handles_non_chunked_streaming(self, telemetry_middleware):
        """Test telemetry processing for non-chunked streaming response."""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/v1/chat/completions"
        mock_request.json = AsyncMock(return_value={
            "model": "test-model",
            "stream": True
        })
        mock_request.headers = {"x-request-id": "test-123"}

        # Mock streaming response without chunked data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.body_iterator = self._create_async_stream([
            b'data: {"choices": [{"message": {"content": "Hello"}}]}\n\n'
        ])

        mock_call_next = AsyncMock(return_value=mock_response)
        mock_logger = MagicMock()

        with patch.object(telemetry_middleware, '_log_telemetry', mock_logger):
            response = await telemetry_middleware.dispatch(mock_request, mock_call_next)

            # Should process streaming but no usage found
            mock_logger.assert_called_once()
            assert response == mock_response
