#!/usr/bin/env python3
"""Unit tests for streaming control middleware."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request, Response

from src.middleware.streaming_control.middleware import StreamingControlMiddleware


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url = MagicMock()
    request.url.path = "/chat/completions"
    request.headers = {}
    return request


@pytest.fixture
def mock_call_next():
    """Create a mock call_next function."""
    async def call_next(request):
        return Response(content=b'{"choices":[]}', status_code=200)
    return call_next


@pytest.mark.asyncio
async def test_streaming_disabled_removes_stream_param(mock_request, mock_call_next):
    """Test that stream parameter is removed when streaming is disabled."""
    body = {"model": "gpt-5", "messages": [], "stream": True}
    body_bytes = json.dumps(body).encode("utf-8")
    mock_request.body = AsyncMock(return_value=body_bytes)

    middleware = StreamingControlMiddleware(app=None, allow_streaming=False)
    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    # Verify the request body was modified
    assert hasattr(mock_request, '_body')
    modified_body = json.loads(mock_request._body.decode("utf-8"))
    assert "stream" not in modified_body or modified_body["stream"] is False


@pytest.mark.asyncio
async def test_streaming_enabled_preserves_stream_param(mock_request, mock_call_next):
    """Test that stream parameter is preserved when streaming is enabled."""
    body = {"model": "gpt-5", "messages": [], "stream": True}
    body_bytes = json.dumps(body).encode("utf-8")
    mock_request.body = AsyncMock(return_value=body_bytes)

    middleware = StreamingControlMiddleware(app=None, allow_streaming=True)
    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    # Request should not be modified
    assert not hasattr(mock_request, '_body')


@pytest.mark.asyncio
async def test_non_post_request_passes_through(mock_request, mock_call_next):
    """Test that non-POST requests pass through unchanged."""
    mock_request.method = "GET"
    body = {"model": "gpt-5", "messages": [], "stream": True}
    body_bytes = json.dumps(body).encode("utf-8")
    mock_request.body = AsyncMock(return_value=body_bytes)

    middleware = StreamingControlMiddleware(app=None, allow_streaming=False)
    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    assert not hasattr(mock_request, '_body')


@pytest.mark.asyncio
async def test_non_completion_path_passes_through(mock_request, mock_call_next):
    """Test that non-completion paths pass through unchanged."""
    mock_request.url.path = "/v1/models"
    body = {"model": "gpt-5", "messages": [], "stream": True}
    body_bytes = json.dumps(body).encode("utf-8")
    mock_request.body = AsyncMock(return_value=body_bytes)

    middleware = StreamingControlMiddleware(app=None, allow_streaming=False)
    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    assert not hasattr(mock_request, '_body')


@pytest.mark.asyncio
async def test_invalid_json_passes_through(mock_request, mock_call_next):
    """Test that invalid JSON passes through without error."""
    body_bytes = b"invalid json"
    mock_request.body = AsyncMock(return_value=body_bytes)

    middleware = StreamingControlMiddleware(app=None, allow_streaming=False)
    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    assert not hasattr(mock_request, '_body')


@pytest.mark.asyncio
async def test_empty_body_passes_through(mock_request, mock_call_next):
    """Test that empty body passes through without error."""
    mock_request.body = AsyncMock(return_value=b"")

    middleware = StreamingControlMiddleware(app=None, allow_streaming=False)
    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    assert not hasattr(mock_request, '_body')
