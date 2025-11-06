#!/usr/bin/env python3
"""Edge-case tests to cover ReasoningFilterMiddleware branches."""

from __future__ import annotations

from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from src.middleware.reasoning_filter.middleware import ReasoningFilterMiddleware


def build_app_echo_raw():
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def echo_raw(req: Request):
        body = await req.body()
        return {"len": len(body)}

    app.add_middleware(ReasoningFilterMiddleware)
    return app


def test_non_json_body_does_not_crash():
    app = build_app_echo_raw()
    client = TestClient(app)
    # Send invalid JSON body to hit JSONDecodeError branch in middleware
    res = client.post("/v1/chat/completions", data="not-json", headers={"content-type": "application/json"})
    assert res.status_code == 200
    assert res.json()["len"] > 0


def test_non_target_path_is_untouched():
    app = build_app_echo_raw()
    client = TestClient(app)
    # GET request should bypass middleware path
    res = client.get("/v1/chat/completions")
    assert res.status_code == 405  # method not allowed


def test_sets_client_request_id_in_log(caplog):
    app = build_app_echo_raw()
    client = TestClient(app)
    with caplog.at_level("DEBUG", logger="litellm_launcher.filter"):
        res = client.post(
            "/v1/chat/completions",
            json={"model": "x", "messages": [], "reasoning": "drop"},
            headers={"x-request-id": "edge-req"},
        )
    assert res.status_code == 200
    msgs = [rec.message for rec in caplog.records]
    assert any("client_request_id" in m and "edge-req" in m for m in msgs)
