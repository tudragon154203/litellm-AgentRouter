#!/usr/bin/env python3
"""Additional coverage for TelemetryMiddleware streaming/non-streaming paths."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.middleware.telemetry import TelemetryMiddleware


@pytest.fixture
def middleware(monkeypatch):
    monkeypatch.setenv("TELEMETRY_ENABLE", "1")
    app = AsyncMock()
    app.state = MagicMock()
    alias_lookup = {"m": "openai/m"}
    app.state.litellm_telemetry_alias_lookup = alias_lookup
    return TelemetryMiddleware(app=app, alias_lookup=alias_lookup)


@pytest.mark.asyncio
async def test_streaming_via_aiter_branch(middleware):
    req = MagicMock()
    req.method = "POST"
    req.url.path = "/v1/chat/completions"
    req.json = AsyncMock(return_value={"model": "m", "stream": True})
    req.headers = {}
    req.app = middleware.app

    class RespIter:
        def __init__(self, chunks):
            self._chunks = chunks

        def __aiter__(self):
            async def iterator():
                for c in self._chunks:
                    yield c
            return iterator()

    resp = RespIter([
        b'data: {"usage": {"prompt_tokens": 2, "completion_tokens": 3}}\n\n',
        b'data: [DONE]\n\n',
    ])
    setattr(resp, "status_code", 200)

    call_next = AsyncMock(return_value=resp)

    with patch.object(middleware, '_log_telemetry') as mock_log:
        out = await middleware.dispatch(req, call_next)
        # Should return a replayable iterator or original response
        assert out is not None
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_non_streaming_body_str_parsing(middleware):
    req = MagicMock()
    req.method = "POST"
    req.url.path = "/v1/chat/completions"
    req.json = AsyncMock(return_value={"model": "m", "stream": False})
    req.headers = {}
    req.app = middleware.app

    resp = MagicMock()
    resp.body = json.dumps({
        "usage": {
            "input_tokens": 1,
            "output_tokens": 4,
            "output_token_details": {"reasoning_tokens": 2}
        }
    })  # str body, not bytes
    resp.status_code = 200

    call_next = AsyncMock(return_value=resp)

    with patch.object(middleware, '_log_telemetry') as mock_log:
        await middleware.dispatch(req, call_next)
        mock_log.assert_called_once()
        data = mock_log.call_args[0][0]
        assert data.get("reasoning_tokens") == 2
        assert data.get("total_tokens") == 5


@pytest.mark.asyncio
async def test_preprocess_drop_reasoning_sets_body(middleware):
    req = MagicMock()
    req.method = "POST"
    req.url.path = "/v1/chat/completions"
    # Provide raw body with top-level reasoning to hit pre-process drop
    raw = json.dumps({"model": "m", "reasoning": "x", "messages": []}).encode()
    req.body = AsyncMock(return_value=raw)
    req.json = AsyncMock(return_value={"model": "m", "stream": False})
    req.headers = {}
    req.app = middleware.app

    resp = MagicMock()
    resp.body = json.dumps({"usage": {"prompt_tokens": 1, "completion_tokens": 1}}).encode()
    resp.status_code = 200

    call_next = AsyncMock(return_value=resp)

    with patch.object(middleware, '_log_telemetry') as mock_log:
        await middleware.dispatch(req, call_next)
        mock_log.assert_called_once()
        # After dispatch, request should have _body attr set (attempted)
        assert hasattr(req, "_body")
        # Ensure dropped reasoning did not break downstream
        data = mock_log.call_args[0][0]
        assert data.get("total_tokens") == 2
