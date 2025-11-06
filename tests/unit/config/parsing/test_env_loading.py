#!/usr/bin/env python3
"""Unit tests for environment-based model spec loading."""

from __future__ import annotations

import pytest

from src.config.parsing import load_model_specs_from_env, load_model_specs_from_cli


class TestLoadModelSpecsFromEnv:
    """Tests for environment-driven spec loading."""

    def test_load_model_specs_from_env_success(self, monkeypatch):
        """Load two models from environment variables."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "gpt5,deepseek")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("MODEL_GPT5_REASONING_EFFORT", "medium")

        monkeypatch.setenv("MODEL_DEEPSEEK_UPSTREAM_MODEL", "deepseek-v3.2")

        specs = load_model_specs_from_env()
        assert [spec.alias for spec in specs] == ["gpt-5", "deepseek-v3.2"]
        assert specs[0].reasoning_effort == "medium"
        assert specs[1].reasoning_effort == "medium"

    def test_load_model_specs_from_env_missing_key(self, monkeypatch):
        """Missing PROXY_MODEL_KEYS should raise ValueError."""
        monkeypatch.delenv("PROXY_MODEL_KEYS", raising=False)
        with pytest.raises(ValueError):
            load_model_specs_from_env()

    def test_legacy_alias_env_var_raises(self, monkeypatch):
        """Legacy MODEL_XXX_ALIAS variables should raise a helpful error."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "test")
        monkeypatch.setenv("MODEL_TEST_ALIAS", "legacy-alias")
        monkeypatch.setenv("MODEL_TEST_UPSTREAM_MODEL", "gpt-5")

        with pytest.raises(
            ValueError,
            match="Legacy environment variable 'MODEL_TEST_ALIAS' detected",
        ):
            load_model_specs_from_env()

    def test_missing_upstream_model_env_var(self, monkeypatch):
        """Test error when MODEL_XXX_UPSTREAM_MODEL is missing."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "test")

        with pytest.raises(ValueError, match="Missing environment variable: MODEL_TEST_UPSTREAM_MODEL"):
            load_model_specs_from_env()

    def test_grok_config_from_environment(self, monkeypatch):
        """Verify Grok can be configured via environment variables."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "grok")
        monkeypatch.setenv("MODEL_GROK_UPSTREAM_MODEL", "grok-code-fast-1")
        monkeypatch.setenv("MODEL_GROK_REASONING_EFFORT", "high")
        monkeypatch.setenv("XAI_API_KEY", "sk-xai-test")

        specs = load_model_specs_from_env()
        assert len(specs) == 1
        assert specs[0].alias == "grok-code-fast-1"
        assert specs[0].upstream_model == "grok-code-fast-1"
        assert specs[0].reasoning_effort == "high"

    def test_glm_config_from_environment(self, monkeypatch):
        """Verify GLM can be configured via environment variables."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "glm")
        monkeypatch.setenv("MODEL_GLM_UPSTREAM_MODEL", "glm-4.6")
        monkeypatch.setenv("GLM_API_KEY", "sk-glm-test")

        specs = load_model_specs_from_env()
        assert len(specs) == 1
        assert specs[0].alias == "glm-4.6"
        assert specs[0].upstream_model == "glm-4.6"
        assert specs[0].reasoning_effort == "none"


class TestLoadModelSpecsFromCli:
    """Tests for CLI-based model spec loading."""

    def test_load_model_specs_empty_args(self):
        """Test load_model_specs_from_cli with no arguments."""
        result = load_model_specs_from_cli(None)
        assert result == []
        result2 = load_model_specs_from_cli([])
        assert result2 == []
