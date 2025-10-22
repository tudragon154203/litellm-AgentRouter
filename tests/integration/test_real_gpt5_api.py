#!/usr/bin/env python3
"""Real integration tests that make actual GPT-5 API calls."""

from __future__ import annotations

import os
import time
from typing import Dict, Any

import pytest

from src.utils import load_dotenv_files


class TestRealGPT5API:
    """Integration tests that make real GPT-5 API calls."""

    @classmethod
    def setup_class(cls):
        """Setup for all tests - load environment variables."""
        load_dotenv_files()
        cls.api_key = os.getenv("OPENAI_API_KEY")
        if not cls.api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")

    def test_gpt5_basic_completion(self):
        """Test basic GPT-5 completion with a simple prompt."""
        import litellm

        response = litellm.completion(
            model="gpt-5",
            messages=[{"role": "user", "content": "Say 'Hello from GPT-5' in exactly those words."}],
            max_tokens=50,
            temperature=0.1,
            api_key=self.api_key
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

        # Assert the response contains what we asked for
        content = message.content.strip()
        assert "Hello from GPT-5" in content

        # Assert usage information is present
        assert hasattr(response, 'usage')
        assert response.usage is not None
        assert response.usage.total_tokens > 0
        assert response.usage.prompt_tokens > 0
        assert response.usage.completion_tokens > 0

    def test_gpt5_with_system_message(self):
        """Test GPT-5 completion with a system message."""
        import litellm

        response = litellm.completion(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that always responds with exactly 3 words."},
                {"role": "user", "content": "What is 2+2?"}
            ],
            max_tokens=100,
            temperature=0.0,
            api_key=self.api_key
        )

        # Assert response
        message = response.choices[0].message
        content = message.content.strip()

        # Should be exactly 3 words (accounting for potential punctuation)
        words = content.split()
        assert len(words) == 3, f"Expected 3 words, got: {content}"

        # Should answer the question correctly
        assert any(word in ["4", "four"] for word in words.lower())

    def test_gpt5_streaming_response(self):
        """Test GPT-5 streaming response."""
        import litellm

        chunks = []
        for chunk in litellm.completion(
            model="gpt-5",
            messages=[{"role": "user", "content": "Count from 1 to 3, one number per line."}],
            max_tokens=50,
            temperature=0.0,
            stream=True,
            api_key=self.api_key
        ):
            chunks.append(chunk)

        # Assert we received chunks
        assert len(chunks) > 0

        # Collect the full content
        full_content = ""
        for chunk in chunks:
            if chunk.choices and chunk.choices[0].delta.content:
                full_content += chunk.choices[0].delta.content

        # Assert the content contains what we expect
        assert "1" in full_content
        assert "2" in full_content
        assert "3" in full_content

    def test_gpt5_error_handling_invalid_model(self):
        """Test GPT-5 error handling with an invalid model."""
        import litellm
        from litellm import AuthenticationError, APIError

        # Test with a non-existent model
        with pytest.raises((APIError, AuthenticationError)) as exc_info:
            litellm.completion(
                model="gpt-5-nonexistent",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
                api_key=self.api_key
            )

        # Assert we get a meaningful error
        assert exc_info.value is not None

    def test_gpt5_temperature_and_max_tokens(self):
        """Test GPT-5 with different temperature and max_tokens settings."""
        import litellm

        # Test with low temperature (should be deterministic)
        response1 = litellm.completion(
            model="gpt-5",
            messages=[{"role": "user", "content": "Say the word: deterministic"}],
            max_tokens=10,
            temperature=0.0,
            api_key=self.api_key
        )

        response2 = litellm.completion(
            model="gpt-5",
            messages=[{"role": "user", "content": "Say the word: deterministic"}],
            max_tokens=10,
            temperature=0.0,
            api_key=self.api_key
        )

        # With temperature 0.0, responses should be very similar
        content1 = response1.choices[0].message.content.strip()
        content2 = response2.choices[0].message.content.strip()

        assert "deterministic" in content1.lower()
        assert "deterministic" in content2.lower()

        # Test max_tokens enforcement
        response = litellm.completion(
            model="gpt-5",
            messages=[{"role": "user", "content": "Write a very long essay about nothing"}],
            max_tokens=5,
            temperature=0.0,
            api_key=self.api_key
        )

        # Should respect max_tokens limit
        assert response.usage.completion_tokens <= 5

    def test_gpt5_json_response_format(self):
        """Test GPT-5 with JSON response format."""
        import litellm

        response = litellm.completion(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You must respond with valid JSON only."},
                {"role": "user", "content": 'Create a JSON object with keys "name" and "age"'}
            ],
            max_tokens=100,
            temperature=0.0,
            response_format={"type": "json_object"},
            api_key=self.api_key
        )

        content = response.choices[0].message.content.strip()

        # Try to parse as JSON
        import json
        parsed = json.loads(content)

        assert isinstance(parsed, dict)
        assert "name" in parsed
        assert "age" in parsed

    def test_gpt5_performance_metrics(self):
        """Test GPT-5 performance and collect metrics."""
        import litellm

        start_time = time.time()

        response = litellm.completion(
            model="gpt-5",
            messages=[{"role": "user", "content": "What is the capital of France? Answer in one word."}],
            max_tokens=10,
            temperature=0.0,
            api_key=self.api_key
        )

        end_time = time.time()
        response_time = end_time - start_time

        # Assert reasonable response time (should be under 30 seconds)
        assert response_time < 30.0, f"Response took too long: {response_time}s"

        # Assert correct answer
        content = response.choices[0].message.content.strip().lower()
        assert "paris" in content

        # Assert token usage is reasonable
        assert response.usage.total_tokens > 0
        assert response.usage.total_tokens < 1000  # Should be much less for this simple query

    def test_gpt5_conversation_context(self):
        """Test GPT-5 maintaining conversation context."""
        import litellm

        conversation = [
            {"role": "user", "content": "My favorite color is blue."},
            {"role": "assistant", "content": "I'll remember that your favorite color is blue."},
            {"role": "user", "content": "What did I just say my favorite color was?"}
        ]

        response = litellm.completion(
            model="gpt-5",
            messages=conversation,
            max_tokens=50,
            temperature=0.0,
            api_key=self.api_key
        )

        content = response.choices[0].message.content.strip().lower()
        assert "blue" in content

    def test_gpt5_with_functions_tools(self):
        """Test GPT-5 with function calling/tool use if available."""
        import litellm

        # Define a simple function
        functions = [
            {
                "name": "get_weather",
                "description": "Get the current weather in a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        }
                    },
                    "required": ["location"]
                }
            }
        ]

        response = litellm.completion(
            model="gpt-5",
            messages=[
                {"role": "user", "content": "What's the weather like in New York?"}
            ],
            functions=functions,
            function_call="auto",
            max_tokens=100,
            temperature=0.0,
            api_key=self.api_key
        )

        # The response should either call the function or explain it can't
        message = response.choices[0].message

        # Check if function call was attempted
        if hasattr(message, 'function_call') and message.function_call:
            assert message.function_call.name == "get_weather"
        else:
            # If no function call, should explain limitation
            content = message.content.strip().lower()
            assert any(word in content for word in ["weather", "new york", "can't", "unable"])

    def test_gpt5_cost_tracking(self):
        """Test GPT-5 token usage for cost estimation."""
        import litellm

        # Make a request with known token count
        response = litellm.completion(
            model="gpt-5",
            messages=[{"role": "user", "content": "Hello, world!"}],
            max_tokens=20,
            temperature=0.0,
            api_key=self.api_key
        )

        usage = response.usage

        # Assert all usage metrics are present and reasonable
        assert usage.prompt_tokens > 0
        assert usage.completion_tokens > 0
        assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens

        # Log for cost analysis (in a real scenario, you'd track costs)
        print(f"Token usage - Prompt: {usage.prompt_tokens}, "
              f"Completion: {usage.completion_tokens}, "
              f"Total: {usage.total_tokens}")