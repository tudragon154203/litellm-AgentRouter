#!/usr/bin/env python3
from __future__ import annotations

import json
import pytest

from src.middleware.telemetry.usage import (
    parse_usage_from_response,
    parse_usage_from_stream_chunk,
    to_usage_tokens,
)
from src.middleware.telemetry.events import UsageTokens


class TestUsageParsing:
    """Test usage extraction from various response formats."""

    def test_parse_usage_openai_format(self):
        """Parse standard OpenAI usage format."""
        response = {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        result = parse_usage_from_response(response)
        assert result == {"prompt": 10, "completion": 20, "total": 30, "reasoning": None}

    def test_parse_usage_anthropic_format(self):
        """Parse Anthropic-style usage with input/output tokens."""
        response = {
            "usage": {
                "input_tokens": 15,
                "output_tokens": 25
            }
        }
        result = parse_usage_from_response(response)
        assert result == {"prompt": 15, "completion": 25, "total": 40, "reasoning": None}

    def test_parse_usage_with_reasoning_tokens(self):
        """Parse usage with reasoning tokens (o1 models)."""
        response = {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 30,
                "total_tokens": 40,
                "output_token_details": {
                    "reasoning_tokens": 15
                }
            }
        }
        result = parse_usage_from_response(response)
        assert result == {"prompt": 10, "completion": 30, "total": 40, "reasoning": 15}

    def test_parse_usage_missing_usage_field(self):
        """Return None when usage field is missing."""
        response = {"choices": [{"message": {"content": "test"}}]}
        result = parse_usage_from_response(response)
        assert result is None

    def test_parse_usage_empty_usage_field(self):
        """Return None when usage field is empty."""
        response = {"usage": None}
        result = parse_usage_from_response(response)
        assert result is None

    def test_parse_stream_chunk_sse_format(self):
        """Parse usage from SSE stream chunk."""
        chunk = 'data: {"usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}}\n\n'
        result = parse_usage_from_stream_chunk(chunk)
        assert result == {"prompt": 5, "completion": 10, "total": 15, "reasoning": None}

    def test_parse_stream_chunk_with_done_marker(self):
        """Handle [DONE] marker in SSE stream."""
        chunk = 'data: [DONE]\n\n'
        result = parse_usage_from_stream_chunk(chunk)
        assert result is None

    def test_parse_stream_chunk_plain_json(self):
        """Parse plain JSON chunk (fallback)."""
        chunk = '{"usage": {"prompt_tokens": 8, "completion_tokens": 12}}'
        result = parse_usage_from_stream_chunk(chunk)
        assert result == {"prompt": 8, "completion": 12, "total": 20, "reasoning": None}

    def test_parse_stream_chunk_invalid_json(self):
        """Return None for invalid JSON."""
        chunk = 'not valid json'
        result = parse_usage_from_stream_chunk(chunk)
        assert result is None

    def test_parse_stream_chunk_multiline_sse(self):
        """Parse multiline SSE with usage in last chunk."""
        chunk = '''data: {"choices": [{"delta": {"content": "test"}}]}

data: {"usage": {"prompt_tokens": 3, "completion_tokens": 7, "total_tokens": 10}}

'''
        result = parse_usage_from_stream_chunk(chunk)
        assert result == {"prompt": 3, "completion": 7, "total": 10, "reasoning": None}

    def test_to_usage_tokens_converts_dict(self):
        """Convert dict to UsageTokens dataclass."""
        usage_dict = {"total": 100, "prompt": 40, "completion": 60, "reasoning": 20}
        result = to_usage_tokens(usage_dict)
        assert isinstance(result, UsageTokens)
        assert result.total == 100
        assert result.prompt == 40
        assert result.completion == 60
        assert result.reasoning == 20

    def test_to_usage_tokens_handles_none(self):
        """Return None when input is None."""
        result = to_usage_tokens(None)
        assert result is None

    def test_to_usage_tokens_handles_missing_fields(self):
        """Handle missing fields gracefully."""
        usage_dict = {"total": 50}
        result = to_usage_tokens(usage_dict)
        assert result.total == 50
        assert result.prompt is None
        assert result.completion is None
        assert result.reasoning is None
