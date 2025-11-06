#!/usr/bin/env python3
"""Additional coverage for ReasoningFilterMiddleware branches."""

from __future__ import annotations

from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from src.middleware.reasoning_filter import ReasoningFilterMiddleware


def build_app_echo_json():
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def echo(req: Request):
        return await req.json()

    app.add_middleware(ReasoningFilterMiddleware)
    return app


def build_app_echo_raw():
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def echo(req: Request):
        body = await req.body()
        return {"len": len(body)}

    app.add_middleware(ReasoningFilterMiddleware)
    return app


def test_empty_body_no_crash():
    app = build_app_echo_raw()
    client = TestClient(app)
    # Send empty raw body to hit branch where body_bytes is falsy
    res = client.post("/v1/chat/completions", data=b"", headers={"content-type": "application/json"})
    # Should not 5xx
    assert 200 <= res.status_code < 500


def test_receive_replacement_applied():
    app = build_app_echo_json()
    client = TestClient(app)
    payload = {"model": "m", "messages": [], "reasoning": "drop"}
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    # Confirm 'reasoning' removed and body successfully parsed via replaced receiver
    data = res.json()
    assert "reasoning" not in data
