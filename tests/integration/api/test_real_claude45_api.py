#!/usr/bin/env python3
"""Real integration tests that make actual Claude 4.5 API calls via Hubs."""

from __future__ import annotations

from tests.integration.api.base_model_test import BaseModelTest, ModelConfig


class TestRealClaude45API(BaseModelTest):
    """Integration tests that make real Claude 4.5 API calls via Hubs."""

    model_config = ModelConfig(
        model_name='openai/claude-4.5-sonnet',
        api_key_env='UPSTREAM_HUBS_API_KEY',
        base_url_env='UPSTREAM_HUBS_BASE_URL',
        default_base_url='https://hubs02225.snia.ch/v1',
    )

    def test_with_system_message(self):
        """Test Claude 4.5 completion with a system message."""
        response = self._call_api_not_stream(
            messages=[
                {"role": "system", "content": "You are a helpful math tutor."},
                {"role": "user", "content": "What is 2+2?"}
            ],
            max_tokens=1000,
            temperature=0.7,
        )

        message = response.choices[0].message
        content = self._extract_content(message)
        assert len(content) > 0, "Response content should not be empty"
        assert any(word in content.lower() for word in ["4", "four"])

    def test_multi_turn_conversation(self):
        """Test Claude 4.5 with a multi-turn conversation."""
        response = self._call_api_not_stream(
            messages=[
                {"role": "user", "content": "My name is Alice."},
                {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
                {"role": "user", "content": "What is my name?"}
            ],
            max_tokens=1000,
            temperature=0.7,
        )

        message = response.choices[0].message
        content = self._extract_content(message)
        assert len(content) > 0, "Response content should not be empty"
        assert "alice" in content.lower(), "Should remember the user's name from conversation history"

    def test_with_low_temperature(self):
        """Test Claude 4.5 with low temperature for deterministic responses."""
        response = self._call_api_not_stream(
            messages=[{"role": "user", "content": "What is the capital of France?"}],
            max_tokens=500,
            temperature=0.0,
        )

        message = response.choices[0].message
        content = self._extract_content(message)
        assert len(content) > 0, "Response content should not be empty"
        assert "paris" in content.lower(), "Should correctly identify Paris as the capital of France"
