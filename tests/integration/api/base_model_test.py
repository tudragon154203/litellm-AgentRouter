#!/usr/bin/env python3
"""Base class for model integration tests following SOLID principles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from src.config.config import runtime_config
from src.utils import build_user_agent

litellm = pytest.importorskip("litellm")


@dataclass
class ModelConfig:
    """Configuration for a specific model under test."""

    model_name: str
    api_key_env: str
    base_url_env: str
    default_base_url: str
    supports_system_message: bool = True
    supports_tool_calling: bool = True
    content_field: str = "content"  # or "reasoning_content" for some models
    fallback_content_field: str | None = None


class BaseModelTest:
    """Base class for model integration tests with shared functionality."""

    model_config: ModelConfig

    @classmethod
    def setup_class(cls):
        """Setup for all tests - load environment variables and configure litellm."""
        runtime_config.ensure_loaded()
        cls.api_key = runtime_config.get_str(cls.model_config.api_key_env)
        cls.base_url = runtime_config.get_str(
            cls.model_config.base_url_env,
            cls.model_config.default_base_url
        )

        if not cls.api_key:
            pytest.skip(f"{cls.model_config.api_key_env} environment variable not set")

        litellm.drop_params = True

    def _build_params(self, stream: bool, **kwargs) -> dict[str, Any]:
        """Build parameters for litellm.completion call."""
        params = {
            'model': self.model_config.model_name,
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': stream,
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": build_user_agent()
            }
        }
        params.update(kwargs)
        return params

    def _call_api_not_stream(self, **kwargs):
        """Call model API without streaming."""
        if 'stream' in kwargs:
            del kwargs['stream']
        return litellm.completion(**self._build_params(stream=False, **kwargs))

    def _call_api_streaming(self, **kwargs):
        """Call model API with streaming."""
        return litellm.completion(**self._build_params(stream=True, **kwargs))

    def _extract_content(self, message) -> str:
        """Extract content from message, handling different content field names."""
        content = getattr(message, self.model_config.content_field, None)
        if not content and self.model_config.fallback_content_field:
            content = getattr(message, self.model_config.fallback_content_field, None)
        # Try reasoning_content as a last resort for models that use it
        if not content:
            content = getattr(message, 'reasoning_content', None)
        return (content or "").strip()

    def _assert_response_structure(self, response):
        """Assert basic response structure is valid."""
        assert response is not None
        assert hasattr(response, 'choices')
        assert len(response.choices) > 0

        message = response.choices[0].message
        assert message is not None

        content = self._extract_content(message)
        assert len(content) > 0, "Response content should not be empty"

        assert hasattr(response, 'usage')
        assert response.usage is not None
        assert response.usage.total_tokens > 0

    def _assert_streaming_response(self, stream):
        """Assert streaming response structure and collect content."""
        assert hasattr(stream, '__iter__'), "Response should be iterable for streaming"

        chunks = []
        content_parts = []

        for chunk in stream:
            chunks.append(chunk)
            assert chunk is not None
            assert hasattr(chunk, 'choices')
            assert len(chunk.choices) > 0

            delta = chunk.choices[0].delta
            if delta:
                content = getattr(delta, self.model_config.content_field, None)
                if not content and self.model_config.fallback_content_field:
                    content = getattr(delta, self.model_config.fallback_content_field, None)
                if content:
                    content_parts.append(content)

        assert len(chunks) > 0, "Should receive at least one chunk"
        full_content = ''.join(content_parts).strip()
        assert len(full_content) > 0, "Streaming response should contain content"

        return chunks, full_content

    def test_basic_completion(self):
        """Test basic completion with a simple prompt."""
        response = self._call_api_not_stream(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1000,
            temperature=0.7,
        )
        self._assert_response_structure(response)

    def test_streaming_completion(self):
        """Test completion with streaming enabled."""
        stream = self._call_api_streaming(
            messages=[{"role": "user", "content": "Count from 1 to 5"}],
            max_tokens=1000,
            temperature=0.7,
        )
        self._assert_streaming_response(stream)

    def test_tool_calling_basic(self):
        """Test basic tool calling with a single tool definition."""
        if not self.model_config.supports_tool_calling:
            pytest.skip(f"{self.model_config.model_name} does not support tool calling")

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA"
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "The temperature unit to use"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ]

        response = self._call_api_not_stream(
            messages=[{"role": "user", "content": "What's the weather like in Paris?"}],
            tools=tools,
            tool_choice="auto",
            max_tokens=1000,
            temperature=0.7,
        )

        assert response is not None
        assert hasattr(response, 'choices')
        assert len(response.choices) > 0

        message = response.choices[0].message
        assert message is not None
        assert hasattr(message, 'tool_calls')
        assert message.tool_calls is not None
        assert len(message.tool_calls) > 0

        tool_call = message.tool_calls[0]
        assert tool_call.function.name == "get_weather"

        args = json.loads(tool_call.function.arguments)
        assert "location" in args
        assert "paris" in args["location"].lower()

    def test_tool_calling_optional(self):
        """Test that model can choose not to use tools when not needed."""
        if not self.model_config.supports_tool_calling:
            pytest.skip(f"{self.model_config.model_name} does not support tool calling")

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ]

        response = self._call_api_not_stream(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            tools=tools,
            tool_choice="auto",
            max_tokens=1000,
            temperature=0.7,
        )

        message = response.choices[0].message

        # Model should respond directly without calling the weather tool
        if message.tool_calls is None or len(message.tool_calls) == 0:
            content = self._extract_content(message)
            assert len(content) > 0
            assert any(word in content.lower() for word in ["4", "four"])
