#!/usr/bin/env python3
"""Unit tests for environment-based model spec loading."""

from __future__ import annotations

import os
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

    def test_load_models_with_upstream_reference(self, monkeypatch):
        """Test loading models with upstream references."""
        # Define upstreams
        monkeypatch.setenv("UPSTREAM_AGENTROUTER_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("UPSTREAM_AGENTROUTER_API_KEY", "sk-agentrouter-test")
        monkeypatch.setenv("UPSTREAM_HUBS_BASE_URL", "https://api.hubs.com/v1")
        monkeypatch.setenv("UPSTREAM_HUBS_API_KEY", "sk-hubs-test")

        # Define models
        monkeypatch.setenv("PROXY_MODEL_KEYS", "gpt5,claude45")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM", "agentrouter")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("MODEL_CLAUDE45_UPSTREAM", "hubs")
        monkeypatch.setenv("MODEL_CLAUDE45_UPSTREAM_MODEL", "claude-4.5-sonnet")

        specs = load_model_specs_from_env()

        assert len(specs) == 2
        assert specs[0].key == "gpt5"
        assert specs[0].upstream_name == "agentrouter"
        assert specs[0].upstream_base == "https://agentrouter.org/v1"
        assert specs[0].upstream_key_env == "sk-agentrouter-test"

        assert specs[1].key == "claude45"
        assert specs[1].upstream_name == "hubs"
        assert specs[1].upstream_base == "https://api.hubs.com/v1"
        assert specs[1].upstream_key_env == "sk-hubs-test"

    def test_load_models_without_upstream_uses_global_defaults(self, monkeypatch):
        """Test loading models without upstream (uses global defaults)."""
        # Clear any existing upstream definitions and model upstream references
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_") or key.startswith("MODEL_GPT5_UPSTREAM"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("PROXY_MODEL_KEYS", "gpt5")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")

        specs = load_model_specs_from_env()

        assert len(specs) == 1
        assert specs[0].upstream_name is None
        assert specs[0].upstream_base == "https://agentrouter.org/v1"
        assert specs[0].upstream_key_env == "OPENAI_API_KEY"

    def test_case_insensitive_upstream_name_resolution(self, monkeypatch):
        """Test case-insensitive upstream name resolution."""
        monkeypatch.setenv("UPSTREAM_HUBS_BASE_URL", "https://api.hubs.com/v1")
        monkeypatch.setenv("UPSTREAM_HUBS_API_KEY_ENV", "HUBS_API_KEY")

        monkeypatch.setenv("PROXY_MODEL_KEYS", "claude")
        monkeypatch.setenv("MODEL_CLAUDE_UPSTREAM", "HUBS")  # Uppercase
        monkeypatch.setenv("MODEL_CLAUDE_UPSTREAM_MODEL", "claude-4.5-sonnet")

        specs = load_model_specs_from_env()

        assert len(specs) == 1
        assert specs[0].upstream_name == "hubs"  # Normalized to lowercase
        assert specs[0].upstream_base == "https://api.hubs.com/v1"

    def test_error_when_referencing_nonexistent_upstream(self, monkeypatch):
        """Test error when MODEL_<KEY>_UPSTREAM references non-existent upstream."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "gpt5")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM", "nonexistent")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")

        with pytest.raises(ValueError, match="Model 'gpt5' references unknown upstream 'nonexistent'"):
            load_model_specs_from_env()

    def test_backward_compatibility_with_existing_configs(self, monkeypatch):
        """Test backward compatibility with existing single-upstream configs."""
        # Clear any existing upstream definitions and model upstream references
        for key in list(os.environ.keys()):
            if key.startswith("UPSTREAM_") or "_UPSTREAM" in key:
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("PROXY_MODEL_KEYS", "gpt5,deepseek")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("MODEL_DEEPSEEK_UPSTREAM_MODEL", "deepseek-v3.2")

        specs = load_model_specs_from_env()

        assert len(specs) == 2
        # Both should use global defaults
        assert specs[0].upstream_name is None
        assert specs[0].upstream_base == "https://agentrouter.org/v1"
        assert specs[0].upstream_key_env == "OPENAI_API_KEY"
        assert specs[1].upstream_name is None
        assert specs[1].upstream_base == "https://agentrouter.org/v1"
        assert specs[1].upstream_key_env == "OPENAI_API_KEY"
