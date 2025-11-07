#!/usr/bin/env python3
"""Real integration tests that make actual Grok Code Fast-1 API calls via litellm."""

from __future__ import annotations

from tests.integration.api.base_model_test import BaseModelTest, ModelConfig


class TestRealGrokAPI(BaseModelTest):
    """Integration tests that make real Grok Code Fast-1 API calls."""

    model_config = ModelConfig(
        model_name='openai/grok-code-fast-1',
        api_key_env='OPENAI_API_KEY',
        base_url_env='OPENAI_BASE_URL',
        default_base_url='https://agentrouter.org/v1',
    )

    def test_code_generation(self):
        """Test Grok's code generation capabilities."""
        response = self._call_api_not_stream(
            messages=[{"role": "user", "content": "Write a Python hello world function."}],
            max_tokens=200,
            temperature=0.7,
        )
        message = response.choices[0].message
        content = self._extract_content(message)
        assert content
        # Should contain Python code indicators
        assert any(keyword in content.lower() for keyword in ["def", "print", "hello"])
