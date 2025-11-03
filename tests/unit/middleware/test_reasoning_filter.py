import pytest
from starlette.testclient import TestClient
from fastapi import FastAPI, Request

from src.middleware.reasoning_filter import ReasoningFilterMiddleware


@pytest.fixture()
def app():
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def echo(req: Request):
        body = await req.json()
        return body

    app.add_middleware(ReasoningFilterMiddleware)
    return app


def test_strips_top_level_reasoning(app):
    client = TestClient(app)
    payload = {"model": "gpt-5", "reasoning": "high", "messages": []}
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reasoning" not in data
    assert data["model"] == "gpt-5"


def test_keeps_nested_reasoning(app):
    client = TestClient(app)
    payload = {"model": "gpt-5", "messages": [], "metadata": {"reasoning": "keep"}}
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "metadata" in data and data["metadata"]["reasoning"] == "keep"


def test_absent_reasoning_no_log_noise(app, caplog):
    client = TestClient(app)
    with caplog.at_level("DEBUG", logger="litellm_launcher.filter"):
        res = client.post("/v1/chat/completions", json={"model": "gpt-5", "messages": []})
    assert res.status_code == 200
    messages = [rec.message for rec in caplog.records]
    assert all("dropped_param" not in m for m in messages)


def test_present_reasoning_logs_debug_once(app, caplog):
    client = TestClient(app)
    with caplog.at_level("DEBUG", logger="litellm_launcher.filter"):
        res = client.post("/v1/chat/completions", json={"model": "gpt-5", "messages": [], "reasoning": None})
    assert res.status_code == 200
    logged = [rec for rec in caplog.records if "dropped_param" in rec.message]
    assert len(logged) == 1
