#!/usr/bin/env python3
"""Real integration tests that make actual GLM 4.6 API calls via litellm."""

from __future__ import annotations

from tests.integration.api.base_model_test import BaseModelTest, ModelConfig


class TestRealGLMAPI(BaseModelTest):
    """Integration tests that make real GLM 4.6 API calls."""

    model_config = ModelConfig(
        model_name='openai/glm-4.6',
        api_key_env='OPENAI_API_KEY',
        base_url_env='OPENAI_BASE_URL',
        default_base_url='https://agentrouter.org/v1',
        content_field='content',
        fallback_content_field='reasoning_content',
    )

    def test_chinese_text(self):
        """Test GLM's Chinese language capabilities."""
        response = self._call_api_not_stream(
            messages=[{"role": "user", "content": "用中文回答：什么是人工智能？"}],
            max_tokens=100,
            temperature=0.7,
        )
        message = response.choices[0].message
        content = self._extract_content(message)
        assert content
        assert any(char in content for char in "人工智能是")  # Should contain Chinese characters

    def test_reasoning_task(self):
        """Test GLM on a reasoning task."""
        response = self._call_api_not_stream(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "If all roses are flowers and some flowers fade quickly, can we "
                        "conclude that some roses fade quickly? Explain your reasoning."
                    ),
                }
            ],
            max_tokens=200,
            temperature=0.3,
        )
        message = response.choices[0].message
        content = self._extract_content(message)
        assert content
        assert len(content) > 20  # Should provide a reasoned explanation
        reasoning_words = ["because", "therefore", "since", "conclude", "logic"]
        assert any(word in content.lower() for word in reasoning_words) or "cannot" in content.lower()
