#!/usr/bin/env python3
"""HTTP-level integration tests against a running LiteLLM proxy."""

from __future__ import annotations

import requests


def test_proxy_health(proxy_server):
    """Proxy health endpoint should report healthy managed models."""
    response = requests.get(
        f"{proxy_server['base_url']}/health",
        headers=proxy_server["headers"],
        timeout=5,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["healthy_count"] >= 1
    assert payload["unhealthy_count"] == 0


def test_proxy_models(proxy_server):
    """Proxy should advertise configured mock model without external dependencies."""
    response = requests.get(
        f"{proxy_server['base_url']}/v1/models",
        headers=proxy_server["headers"],
        timeout=5,
    )

    assert response.status_code == 200
    models = response.json()["data"]
    advertised = {model["id"] for model in models}
    assert proxy_server["model"] in advertised


def test_proxy_completion(proxy_server):
    """Chat completion endpoint should return mocked content with real server semantics."""
    payload = {
        "model": proxy_server["model"],
        "messages": [{"role": "user", "content": "Hello from integration tests"}],
        "temperature": 0,
    }
    response = requests.post(
        f"{proxy_server['base_url']}/v1/chat/completions",
        headers={**proxy_server["headers"], "Content-Type": "application/json"},
        json={**payload},
        timeout=10,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["choices"], "Expected at least one completion choice"
    content = body["choices"][0]["message"]["content"]
    assert content == proxy_server["mock_response"]
