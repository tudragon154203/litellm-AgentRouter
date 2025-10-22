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

    def _call_gpt5_api_not_stream(self, **kwargs):
        """Helper method to call GPT-5 API (non-streaming only)."""
        import litellm
        import sys

        # Ensure streaming is disabled for this method
        if 'stream' in kwargs:
            del kwargs['stream']

        # Use the same format as the working demo
        default_params = {
            'model': 'openai/gpt-5',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': False,
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": f"QwenCode/0.0.14 ({sys.platform}; {os.getenv('PROCESSOR_ARCHITECTURE', 'unknown')})"
            }
        }
        default_params.update(kwargs)
        return litellm.completion(**default_params)

    def _call_gpt5_api_streaming(self, **kwargs):
        """Helper method to call GPT-5 API with streaming."""
        import litellm
        import sys

        # Use the same format as the working demo
        default_params = {
            'model': 'openai/gpt-5',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': True,
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
        assert any(word in ["4", "four"] for word in content.lower())

    def test_gpt5_streaming_completion(self):
        """Test GPT-5 completion with streaming enabled."""
        import litellm

        response_stream = self._call_gpt5_api_streaming(
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

    def test_gpt5_streaming_vs_non_streaming_performance(self):
        """Compare performance between streaming and non-streaming modes."""
        import litellm
        import time
        import statistics

        test_prompt = "Write a brief explanation of quantum computing in 3 paragraphs"
        test_params = {
            'messages': [{"role": "user", "content": test_prompt}],
            'max_tokens': 500,
            'temperature': 0.7,
        }

        # Measure non-streaming performance
        non_streaming_times = []
        non_streaming_content_lengths = []

        for i in range(3):  # Run multiple times for average
            start_time = time.time()
            response = self._call_gpt5_api(**test_params)
            end_time = time.time()

            non_streaming_times.append(end_time - start_time)
            content_length = len(response.choices[0].message.content or "")
            non_streaming_content_lengths.append(content_length)

        # Measure streaming performance
        streaming_times = []
        streaming_content_lengths = []

        for i in range(3):  # Run multiple times for average
            start_time = time.time()
            response_stream = self._call_gpt5_api_streaming(**test_params)

            content_parts = []
            for chunk in response_stream:
                delta = chunk.choices[0].delta
                if delta and hasattr(delta, 'content') and delta.content:
                    content_parts.append(delta.content)

            end_time = time.time()

            streaming_times.append(end_time - start_time)
            full_content = ''.join(content_parts)
            streaming_content_lengths.append(len(full_content))

        # Calculate averages
        avg_non_streaming_time = statistics.mean(non_streaming_times)
        avg_streaming_time = statistics.mean(streaming_times)
        avg_non_streaming_length = statistics.mean(non_streaming_content_lengths)
        avg_streaming_length = statistics.mean(streaming_content_lengths)

        # Performance assertions
        assert avg_non_streaming_time > 0, "Non-streaming should take positive time"
        assert avg_streaming_time > 0, "Streaming should take positive time"

        # Content should be similar length (within 20% tolerance)
        length_ratio = avg_streaming_length / avg_non_streaming_length if avg_non_streaming_length > 0 else 0
        assert 0.8 <= length_ratio <= 1.2, f"Content length ratio {length_ratio:.2f} should be close to 1.0"

        # Print performance comparison for analysis
        print(f"\nPerformance Comparison:")
        print(f"Non-streaming - Average time: {avg_non_streaming_time:.2f}s, Content length: {avg_non_streaming_length:.0f}")
        print(f"Streaming - Average time: {avg_streaming_time:.2f}s, Content length: {avg_streaming_length:.0f}")
        print(f"Time difference: {avg_non_streaming_time - avg_streaming_time:.2f}s")
        print(f"Streaming speedup: {avg_non_streaming_time / avg_streaming_time:.2f}x" if avg_streaming_time > 0 else "N/A")

        # Basic performance expectations
        # Streaming should complete reasonably close to non-streaming time
        # In many cases, streaming might be slightly faster due to reduced buffering
        time_ratio = avg_streaming_time / avg_non_streaming_time
        assert 0.5 <= time_ratio <= 2.0, f"Time ratio {time_ratio:.2f} should be reasonable"

