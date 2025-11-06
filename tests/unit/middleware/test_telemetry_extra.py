#!/usr/bin/env python3
"""Extra telemetry tests to cover env disable and replay iterator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.middleware.telemetry import TelemetryMiddleware


@pytest.fixture
def middleware():
    app = AsyncMock()
    app.state = MagicMock()
    alias_lookup = {"m": "upstream/m"}
    app.state.litellm_telemetry_alias_lookup = alias_lookup
    return TelemetryMiddleware(app=app, alias_lookup=alias_lookup)


@pytest.mark.asyncio
async def test_env_disable_skips_processing(middleware, monkeypatch):
    monkeypatch.setenv("TELEMETRY_ENABLE", "0")

    req = MagicMock()
    req.method = "POST"
    req.url.path = "/v1/chat/completions"
    req.json = AsyncMock(return_value={"model": "m", "stream": False})

    next_resp = MagicMock()
    call_next = AsyncMock(return_value=next_resp)

    resp = await middleware.dispatch(req, call_next)
    assert resp is next_resp


@pytest.mark.asyncio
async def test_replay_stream_chunks_yields_all(middleware):
    chunks = [b"a", b"b", b"c"]
    it = middleware._replay_stream_chunks(chunks)
    out = []
    async for c in it:
        out.append(c)
    assert out == chunks


@pytest.mark.asyncio
async def test_parse_usage_fallback_fields(middleware):
    payload = {
        "usage": {
            "input_tokens": 3,
            "output_tokens": 7,
            "output_token_details": {"reasoning_tokens": 2},
        }
    }
    usage = middleware._parse_usage_from_response(payload)
    assert usage["prompt_tokens"] == 3
    assert usage["completion_tokens"] == 7
    assert usage["total_tokens"] == 10
    assert usage["output_token_details"]["reasoning_tokens"] == 2
