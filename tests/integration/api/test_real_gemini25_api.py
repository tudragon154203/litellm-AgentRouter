#!/usr/bin/env python3
"""Real integration tests that make actual Gemini 2.5 Pro API calls via Hubs."""

from __future__ import annotations

import pytest

from src.config.config import runtime_config
from src.utils import build_user_agent

litellm = pytest.importorskip("litellm")


class TestRealGemini25API:
    """Integration tests that make real Gemini 2.5 Pro API calls via Hubs."""

    @classmethod
    def setup_class(cls):
        """Setup for all tests - load environment variables."""
        runtime_config.ensure_loaded()
        cls.api_key = runtime_config.get_str("UPSTREAM_HUBS_API_KEY")
        cls.base_url = runtime_config.get_str("UPSTREAM_HUBS_BASE_URL", "https://hubs02225.snia.ch/v1")

        if not cls.api_key:
            pytest.skip("UPSTREAM_HUBS_API_KEY environment variable not set")

        # Set drop_params to handle unsupported parameters
        litellm.drop_params = True

    def _call_gemini25_api_not_stream(self, **kwargs):
        """Helper method to call Gemini 2.5 Pro API (non-streaming only)."""
        # Ensure streaming is disabled for this method
        if 'stream' in kwargs:
            del kwargs['stream']

        default_params = {
            'model': 'openai/gemini-2.5-pro',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': False,
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": build_user_agent()
            }
        }
        default_params.update(kwargs)
        return litellm.completion(**default_params)

    def _call_gemini25_api_streaming(self, **kwargs):
        """Helper method to call Gemini 2.5 Pro API with streaming."""
        default_params = {
            'model': 'openai/gemini-2.5-pro',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': True,
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": build_user_agent()
            }
        }
        default_params.update(kwargs)
        return litellm.completion(**default_params)

    def test_gemini25_basic_completion(self):
        """Test basic Gemini 2.5 Pro completion with a simple prompt."""
        response = self._call_gemini25_api_not_stream(
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

    def test_gemini25_with_system_message(self):
        """Test Gemini 2.5 Pro completion with a system message."""
        response = self._call_gemini25_api_not_stream(
            messages=[
                {"role": "system", "content": "You are a helpful math tutor."},
                {"role": "user", "content": "What is 2+2?"}
            ],
            max_tokens=1000,
            temperature=0.7,
        )

        # Assert response
        message = response.choices[0].message
        content = message.content.strip()

        # Should have some content
        assert len(content) > 0, "Response content should not be empty"

        # Should answer the question correctly
        assert any(word in content.lower() for word in ["4", "four"])

    def test_gemini25_streaming_completion(self):
        """Test Gemini 2.5 Pro completion with streaming enabled."""
        response_stream = self._call_gemini25_api_streaming(
            messages=[{"role": "user", "content": "Count from 1 to 5"}],
            max_tokens=1000,
            temperature=0.7,
        )

        # Assert response is a generator/iterator
        assert hasattr(response_stream, '__iter__'), "Response should be iterable for streaming"

        # Collect all chunks
        chunks = []
        content_parts = []

        for chunk in response_stream:
            chunks.append(chunk)

            # Assert chunk structure
            assert chunk is not None
            assert hasattr(chunk, 'choices')
            assert len(chunk.choices) > 0

            # Get delta content if available
            delta = chunk.choices[0].delta
            if delta and hasattr(delta, 'content') and delta.content:
                content_parts.append(delta.content)

        # Assert we received chunks
        assert len(chunks) > 0, "Should receive at least one chunk"

        # Assert we got some content
        full_content = ''.join(content_parts).strip()
        assert len(full_content) > 0, "Streaming response should contain content"

        # Check usage information if available (may not be present in streaming responses)
        last_chunk = chunks[-1]
        if hasattr(last_chunk, 'usage') and last_chunk.usage:
            assert last_chunk.usage.total_tokens > 0

    def test_gemini25_multi_turn_conversation(self):
        """Test Gemini 2.5 Pro with a multi-turn conversation."""
        response = self._call_gemini25_api_not_stream(
            messages=[
                {"role": "user", "content": "My name is Bob."},
                {"role": "assistant", "content": "Hello Bob! Nice to meet you."},
                {"role": "user", "content": "What is my name?"}
            ],
            max_tokens=1000,
            temperature=0.7,
        )

        # Assert response
        message = response.choices[0].message
        content = message.content.strip()

        # Should have some content
        assert len(content) > 0, "Response content should not be empty"

        # Should remember the name from context
        assert "bob" in content.lower(), "Should remember the user's name from conversation history"

    def test_gemini25_with_low_temperature(self):
        """Test Gemini 2.5 Pro with low temperature for deterministic responses."""
        response = self._call_gemini25_api_not_stream(
            messages=[{"role": "user", "content": "What is the capital of Japan?"}],
            max_tokens=500,
            temperature=0.0,
        )

        # Assert response
        message = response.choices[0].message
        content = message.content.strip()

        # Should have some content
        assert len(content) > 0, "Response content should not be empty"

        # Should contain Tokyo
        assert "tokyo" in content.lower(), "Should correctly identify Tokyo as the capital of Japan"

    def test_gemini25_with_max_tokens_limit(self):
        """Test Gemini 2.5 Pro with max_tokens parameter."""
        response = self._call_gemini25_api_not_stream(
            messages=[{"role": "user", "content": "Write a short sentence about machine learning."}],
            max_tokens=100,
            temperature=0.7,
        )

        # Assert response
        message = response.choices[0].message
        content = message.content.strip()

        # Should have some content
        assert len(content) > 0, "Response content should not be empty"

        # Check usage information
        assert hasattr(response, 'usage')
        assert response.usage is not None
        # Should have reasonable token usage
        assert response.usage.completion_tokens > 0, "Should have completion tokens"
        assert response.usage.total_tokens > 0, "Should have total tokens"

    def test_gemini25_reasoning_task(self):
        """Test Gemini 2.5 Pro with a reasoning task (configured with high reasoning effort)."""
        response = self._call_gemini25_api_not_stream(
            messages=[{
                "role": "user",
                "content": "If a train travels 120 miles in 2 hours, what is its average speed in miles per hour?"
            }],
            max_tokens=1000,
            temperature=0.3,
        )

        # Assert response
        message = response.choices[0].message
        content = message.content.strip()

        # Should have some content
        assert len(content) > 0, "Response content should not be empty"

        # Should contain the correct answer (60 mph)
        assert any(word in content.lower() for word in ["60", "sixty"]), "Should calculate correct average speed"
