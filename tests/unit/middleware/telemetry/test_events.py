#!/usr/bin/env python3
from __future__ import annotations

from src.middleware.telemetry.events import UsageTokens


class TestEvents:
    """Test event dataclass methods."""

    def test_usage_tokens_iter(self):
        """UsageTokens should be iterable."""
        usage = UsageTokens(total=100, prompt=40, completion=60, reasoning=20)
        items = list(usage)
        
        # Should return key-value pairs
        assert len(items) == 4
        assert ("total", 100) in items
        assert ("prompt", 40) in items

    def test_usage_tokens_keys(self):
        """UsageTokens should provide keys()."""
        usage = UsageTokens(total=100, prompt=40, completion=60, reasoning=20)
        keys = usage.keys()
        
        assert "total" in keys
        assert "prompt" in keys
        assert "completion" in keys
        assert "reasoning" in keys

    def test_usage_tokens_values(self):
        """UsageTokens should provide values()."""
        usage = UsageTokens(total=100, prompt=40, completion=60, reasoning=20)
        values = list(usage.values())
        
        assert 100 in values
        assert 40 in values
        assert 60 in values
        assert 20 in values

    def test_usage_tokens_items(self):
        """UsageTokens should provide items()."""
        usage = UsageTokens(total=100, prompt=40, completion=60, reasoning=20)
        items = list(usage.items())
        
        assert ("total", 100) in items
        assert ("prompt", 40) in items
        assert ("completion", 60) in items
        assert ("reasoning", 20) in items
