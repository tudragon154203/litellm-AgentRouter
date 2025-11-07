#!/usr/bin/env python3
"""Unit tests for upstream registry parsing."""

from __future__ import annotations

import os
import pytest

from src.config.parsing import parse_upstream_registry


class TestParseUpstreamRegistry:
    """Tests for upstream registry parsing."""

    def test_parse_valid_upstream_definitions(self, monkeypatch):
        """Parse valid upstream definitions from environment."""
        # Clear existing UPSTREAM_* variables first
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("UPSTREAM_AGENTROUTER_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("UPSTREAM_AGENTROUTER_API_KEY", "sk-test-agentrouter-key")
        monkeypatch.setenv("UPSTREAM_HUBS_BASE_URL", "https://api.hubs.com/v1")
        monkeypatch.setenv("UPSTREAM_HUBS_API_KEY", "sk-test-hubs-key")

        registry = parse_upstream_registry()

        assert len(registry) == 2
        assert "agentrouter" in registry
        assert "hubs" in registry

        agentrouter = registry["agentrouter"]
        assert agentrouter.name == "agentrouter"
        assert agentrouter.base_url == "https://agentrouter.org/v1"
        assert agentrouter.api_key_env == "sk-test-agentrouter-key"

        hubs = registry["hubs"]
        assert hubs.name == "hubs"
        assert hubs.base_url == "https://api.hubs.com/v1"
        assert hubs.api_key_env == "sk-test-hubs-key"

    def test_case_insensitive_upstream_names(self, monkeypatch):
        """Upstream names should be case-insensitive (stored as lowercase)."""
        # Clear existing UPSTREAM_* variables first
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("UPSTREAM_HUBS_BASE_URL", "https://api.hubs.com/v1")
        monkeypatch.setenv("UPSTREAM_HUBS_API_KEY", "sk-test-key-1")
        monkeypatch.setenv("UPSTREAM_hubs_BASE_URL", "https://api.hubs2.com/v1")
        monkeypatch.setenv("UPSTREAM_hubs_API_KEY", "sk-test-key-2")

        registry = parse_upstream_registry()

        # Should only have one entry (lowercase 'hubs')
        # Last one wins due to dict overwrite
        assert len(registry) == 1
        assert "hubs" in registry
        assert registry["hubs"].base_url == "https://api.hubs2.com/v1"
        assert registry["hubs"].api_key_env == "sk-test-key-2"

    def test_incomplete_upstream_missing_base_url(self, monkeypatch):
        """Upstream with only API_KEY should raise ValueError."""
        # Clear existing UPSTREAM_* variables first
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("UPSTREAM_INCOMPLETE_API_KEY", "sk-incomplete-key")

        with pytest.raises(ValueError, match="Upstream 'incomplete' is incomplete"):
            parse_upstream_registry()

    def test_incomplete_upstream_missing_api_key(self, monkeypatch):
        """Upstream with only BASE_URL should raise ValueError."""
        # Clear existing UPSTREAM_* variables first
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("UPSTREAM_INCOMPLETE_BASE_URL", "https://incomplete.com/v1")

        with pytest.raises(ValueError, match="Upstream 'incomplete' is incomplete"):
            parse_upstream_registry()

    def test_incomplete_upstream_missing_api_key_env(self, monkeypatch):
        """Alias for test_incomplete_upstream_missing_api_key for backward compatibility."""
        self.test_incomplete_upstream_missing_api_key(monkeypatch)

    def test_empty_registry(self, monkeypatch):
        """No UPSTREAM_* variables should return empty registry."""
        # Clear any existing UPSTREAM_* variables
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_"):
                monkeypatch.delenv(key, raising=False)

        registry = parse_upstream_registry()
        assert registry == {}

    def test_malformed_upstream_variable_ignored(self, monkeypatch):
        """Malformed UPSTREAM_ variables should be ignored."""
        # Clear existing UPSTREAM_* variables first
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("UPSTREAM_", "invalid")
        monkeypatch.setenv("UPSTREAM_NOFIELD", "invalid")

        registry = parse_upstream_registry()
        assert registry == {}

    def test_multiple_upstreams_with_mixed_case(self, monkeypatch):
        """Test multiple upstreams with various case combinations."""
        # Clear existing UPSTREAM_* variables first
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("UPSTREAM_AgentRouter_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("UPSTREAM_AGENTROUTER_API_KEY", "sk-agentrouter-key")
        monkeypatch.setenv("UPSTREAM_hubs_BASE_URL", "https://hubs.com/v1")
        monkeypatch.setenv("UPSTREAM_HUBS_API_KEY", "sk-hubs-key")

        registry = parse_upstream_registry()

        assert len(registry) == 2
        assert "agentrouter" in registry
        assert "hubs" in registry
        assert registry["agentrouter"].base_url == "https://agentrouter.org/v1"
        assert registry["hubs"].base_url == "https://hubs.com/v1"
