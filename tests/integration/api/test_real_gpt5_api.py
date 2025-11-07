#!/usr/bin/env python3
"""Real integration tests that make actual GPT-5 API calls."""

from __future__ import annotations

from tests.integration.api.base_model_test import BaseModelTest, ModelConfig


class TestRealGPT5API(BaseModelTest):
    """Integration tests that make real GPT-5 API calls."""

    model_config = ModelConfig(
        model_name='openai/gpt-5',
        api_key_env='OPENAI_API_KEY',
        base_url_env='OPENAI_BASE_URL',
        default_base_url='https://agentrouter.org/v1',
    )

    def test_with_system_message(self):
        """Test GPT-5 completion with a system message."""
        response = self._call_api_not_stream(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            max_tokens=1000,
            temperature=0.7,
        )

        message = response.choices[0].message
        content = self._extract_content(message)
        assert len(content) > 0, "Response content should not be empty"
        assert any(word in ["4", "four"] for word in content.lower())
