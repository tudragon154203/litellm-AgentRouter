#!/usr/bin/env python3
"""Integration test exercising the official OpenAI client against the local proxy."""

from __future__ import annotations

import pytest

openai = pytest.importorskip("openai")


def test_openai_chat_completion(proxy_server):
    """OpenAI client should retrieve the mocked completion from the running proxy."""
    client = openai.OpenAI(
        base_url=proxy_server["base_url"],
        api_key=proxy_server["master_key"],
    )

    response = client.chat.completions.create(
        model=proxy_server["model"],
        messages=[{"role": "user", "content": "Say hello"}],
        temperature=0,
    )

    assert response.choices, "Expected at least one completion choice"
    assert response.choices[0].message.content == proxy_server["mock_response"]
