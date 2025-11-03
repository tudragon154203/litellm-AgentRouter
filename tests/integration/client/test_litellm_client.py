#!/usr/bin/env python3
"""Client integration tests exercising the LiteLLM SDK against the local proxy."""

from __future__ import annotations

import litellm


def test_litellm_client(proxy_server):
    """LiteLLM client should successfully invoke the running proxy."""
    litellm.drop_params = True  # Ensure drop_params aligns with proxy defaults
    response = litellm.completion(
        model=f"openai/{proxy_server['model']}",
        messages=[{"role": "user", "content": "Say hello"}],
        api_base=proxy_server["base_url"],
        api_key=proxy_server["master_key"],
        temperature=0.5,
    )

    message = response.choices[0].message.content
    assert message == proxy_server["mock_response"]
    assert response.model.endswith(proxy_server["upstream_model"])
