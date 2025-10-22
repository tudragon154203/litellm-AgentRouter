#!/usr/bin/env python3
"""Real integration tests that make actual GPT-5 API calls."""

from __future__ import annotations

import os
import sys

import pytest

from src.utils import load_dotenv_files


class TestRealGPT5API:
    """Integration tests that make real GPT-5 API calls."""

    @classmethod
    def setup_class(cls):
        """Setup for all tests - load environment variables."""
        load_dotenv_files()
        cls.api_key = os.getenv("OPENAI_API_KEY")
        cls.base_url = os.getenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")

        if not cls.api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")

        # Set drop_params to handle unsupported parameters for GPT-5
        import litellm
        litellm.drop_params = True

    def _call_gpt5_api(self, **kwargs):
        """Helper method to call GPT-5 API."""
        import litellm
        import sys

        # Use the same format as the working demo
        default_params = {
            'model': 'openai/gpt-5',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": f"QwenCode/0.0.14 ({sys.platform}; {os.getenv('PROCESSOR_ARCHITECTURE', 'unknown')})"
            }
        }
        default_params.update(kwargs)
        return litellm.completion(**default_params)

    def test_gpt5_basic_completion(self):
        """Test basic GPT-5 completion with a simple prompt."""
        import litellm

        response = self._call_gpt5_api(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1000,
            temperature=0.7,
        )

        # Assert response structure
        assert response is not None
        assert hasattr(response, 'choices')
        assert len(response.choices) > 0

        # Get the message content
        message = response.choices[0].message
        assert message is not None
        assert hasattr(message, 'content')
        assert message.content is not None

        # Assert the response contains some content
        content = message.content.strip()
        assert len(content) > 0, "Response content should not be empty"

        # Assert usage information is present
        assert hasattr(response, 'usage')
        assert response.usage is not None
        assert response.usage.total_tokens > 0

    def test_gpt5_with_system_message(self):
        """Test GPT-5 completion with a system message."""
        import litellm

        response = self._call_gpt5_api(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that always responds with exactly 3 words."},
                {"role": "user", "content": "What is 2+2?"}
            ],
            max_tokens=100,
            temperature=0.7,
        )

        # Assert response
        message = response.choices[0].message
        content = message.content.strip()

        # Should be roughly 3 words (accounting for potential punctuation)
        words = content.split()
        assert len(words) <= 5, f"Expected roughly 3 words, got: {content}"

        # Should answer the question correctly
        assert any(word in ["4", "four"] for word in words.lower())

