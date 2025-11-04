#!/usr/bin/env python3
"""Unit tests for src.config using the multi-model schema."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from src.config.models import ModelSpec
from src.config.parsing import prepare_config, load_model_specs_from_env
from src.config.rendering import render_config
from src.utils import create_temp_config_if_needed


def make_spec(
    *,
    key: str,
    alias: str,
    upstream_model: str,
    reasoning_effort: str | None = None,
    upstream_base: str | None = None,
    upstream_key_env: str | None = None,
) -> ModelSpec:
    """Helper to create a ModelSpec with defaults."""
    return ModelSpec(
        key=key,
        alias=alias,
        upstream_model=upstream_model,
        upstream_base=upstream_base,
        upstream_key_env=upstream_key_env,
        reasoning_effort=reasoning_effort,
    )


class TestRenderConfig:
    """Tests for render_config."""

    def test_render_config_single_model(self):
        """Render config for one model and include reasoning effort."""
        spec = make_spec(
            key="gpt5",
            alias="gpt-5",
            upstream_model="gpt-5",
            reasoning_effort="medium",
        )
        config_text = render_config(
            model_specs=[spec],
            global_upstream_base="https://agentrouter.org/v1",
            global_upstream_key_env="OPENAI_API_KEY",
            master_key="sk-master",
            drop_params=True,
            streaming=True,
        )

        parsed = yaml.safe_load(config_text)
        assert parsed["model_list"][0]["model_name"] == "gpt-5"
        assert parsed["model_list"][0]["litellm_params"]["model"] == "openai/gpt-5"
        assert parsed["model_list"][0]["litellm_params"]["reasoning_effort"] == "medium"
        assert parsed["general_settings"]["master_key"] == "sk-master"

    def test_render_config_allows_reasoning_for_deepseek(self):
        """Reasoning effort should be preserved for DeepSeek when requested."""
        spec = make_spec(
            key="deepseek",
            alias="deepseek-v3.2",
            upstream_model="deepseek-v3.2",
            reasoning_effort="medium",
        )
        config_text = render_config(
            model_specs=[spec],
            global_upstream_base="https://agentrouter.org/v1",
            global_upstream_key_env="OPENAI_API_KEY",
            master_key=None,
            drop_params=True,
            streaming=False,
        )

        parsed = yaml.safe_load(config_text)
        assert parsed["model_list"][0]["litellm_params"]["reasoning_effort"] == "medium"


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


class TestPrepareConfig:
    """Tests for prepare_config."""

    def test_prepare_config_uses_cli_specs(self, monkeypatch):
        """CLI-provided model specs should be rendered into config."""
        args = SimpleNamespace(
            config=None,
            model_specs=[
                make_spec(
                    key="model1",
                    alias="model-one",
                    upstream_model="gpt-5",
                    reasoning_effort="high",
                )
            ],
            upstream_base=None,
            upstream_key_env=None,
            master_key="sk-cli",
            no_master_key=False,
            drop_params=True,
            streaming=True,
            print_config=False,
        )

        with patch.dict(os.environ, {}, clear=True):
            config_text, is_generated = prepare_config(args)

        assert is_generated is True
        parsed = yaml.safe_load(config_text)
        assert parsed["model_list"][0]["model_name"] == "model-one"
        assert parsed["model_list"][0]["litellm_params"]["reasoning_effort"] == "high"
        assert parsed["general_settings"]["master_key"] == "sk-cli"
        assert args.model_specs  # ensure attribute preserved

    def test_prepare_config_from_env(self, monkeypatch):
        """When CLI specs missing, environment should be used."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "primary")
        monkeypatch.setenv("MODEL_PRIMARY_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

        args = SimpleNamespace(
            config=None,
            model_specs=[],
            upstream_base=None,
            upstream_key_env=None,
            master_key=None,
            no_master_key=True,
            drop_params=True,
            streaming=False,
            print_config=False,
        )

        config_text, is_generated = prepare_config(args)
        assert is_generated is True
        parsed = yaml.safe_load(config_text)
        assert parsed["model_list"][0]["model_name"] == "gpt-5"
        assert parsed["model_list"][0]["litellm_params"]["api_key"] == "os.environ/OPENAI_API_KEY"

    def test_prepare_config_missing_env_errors(self, monkeypatch):
        """Missing environment configuration should exit with error."""
        monkeypatch.delenv("PROXY_MODEL_KEYS", raising=False)
        args = SimpleNamespace(
            config=None,
            model_specs=[],
            upstream_base=None,
            upstream_key_env=None,
            master_key=None,
            no_master_key=True,
            drop_params=True,
            streaming=True,
            print_config=False,
        )

        with pytest.raises(SystemExit):
            prepare_config(args)

    def test_prepare_config_returns_path_for_existing_config(self, tmp_path):
        """Existing config file should be returned as a path with is_generated False."""
        config_path = tmp_path / "litellm-config.yaml"
        config_content = "model_list:\n  - model_name: external\n"
        config_path.write_text(config_content)

        args = SimpleNamespace(
            config=config_path,
            model_specs=None,
            upstream_base=None,
            upstream_key_env=None,
            master_key="unused",
            no_master_key=False,
            drop_params=True,
            streaming=True,
            print_config=False,
        )

        config_data, is_generated = prepare_config(args)
        assert is_generated is False
        assert config_data == config_path

        with create_temp_config_if_needed(config_data, is_generated) as resolved_path:
            assert resolved_path == config_path


class TestTemporaryConfig:
    """Tests for temporary config helper."""

    def test_create_temp_config_if_needed(self, tmp_path):
        """Generated config should be written to a temporary file."""
        config_text = "model_list:\n  - model_name: test\n"

        with create_temp_config_if_needed(config_text, True) as path:
            assert path.exists()
            assert path.read_text() == config_text

        assert not path.exists()


def test_model_spec_post_init():
    """Test __post_init__ method for legacy compatibility - covers models.py:70."""
    from src.config.models import ModelSpec
    spec = ModelSpec(key="test", alias="test-alias", upstream_model="gpt-4")
    # Call __post_init__ explicitly for coverage
    spec.__post_init__()
    # Should complete without error
    assert spec.upstream_model == "gpt-4"


def test_load_model_specs_empty_args():
    """Test load_model_specs_from_cli with no arguments - covers parsing.py:98."""
    from src.config.parsing import load_model_specs_from_cli
    result = load_model_specs_from_cli(None)
    assert result == []
    result2 = load_model_specs_from_cli([])
    assert result2 == []


class TestGrokCodeFast1Integration:
    """Tests for Grok Code Fast-1 model integration."""

    def test_grok_code_fast_1_in_model_caps(self):
        """Verify grok-code-fast-1 is present in MODEL_CAPS."""
        from src.config.models import MODEL_CAPS
        assert "grok-code-fast-1" in MODEL_CAPS

    def test_grok_code_fast_1_supports_reasoning(self):
        """Verify grok-code-fast-1 supports reasoning capability."""
        from src.config.models import get_model_capabilities
        caps = get_model_capabilities("grok-code-fast-1")
        assert caps["supports_reasoning"] is True

    def test_render_config_with_grok_code_fast_1(self):
        """Verify config rendering works correctly for grok-code-fast-1."""
        spec = make_spec(
            key="grok",
            alias="grok-code-fast-1",
            upstream_model="grok-code-fast-1",
            reasoning_effort="medium",
        )
        config_text = render_config(
            model_specs=[spec],
            global_upstream_base="https://api.x.ai/v1",
            global_upstream_key_env="XAI_API_KEY",
            master_key="sk-test",
            drop_params=True,
            streaming=True,
        )

        parsed = yaml.safe_load(config_text)
        assert parsed["model_list"][0]["model_name"] == "grok-code-fast-1"
        assert parsed["model_list"][0]["litellm_params"]["model"] == "openai/grok-code-fast-1"
        assert parsed["model_list"][0]["litellm_params"]["reasoning_effort"] == "medium"

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


class TestGLM46Integration:
    """Tests for GLM-4.6 model integration."""

    def test_glm_4_6_in_model_caps(self):
        """Verify glm-4.6 is present in MODEL_CAPS."""
        from src.config.models import MODEL_CAPS
        assert "glm-4.6" in MODEL_CAPS

    def test_glm_4_6_does_not_support_reasoning(self):
        """Verify glm-4.6 reasoning capability is correctly False."""
        from src.config.models import get_model_capabilities
        caps = get_model_capabilities("glm-4.6")
        assert caps["supports_reasoning"] is False

    def test_render_config_with_glm_4_6(self):
        """Verify config rendering works correctly for glm-4.6."""
        spec = make_spec(
            key="glm",
            alias="glm-4.6",
            upstream_model="glm-4.6",
            reasoning_effort=None,  # GLM doesn't support reasoning
        )
        config_text = render_config(
            model_specs=[spec],
            global_upstream_base="https://open.bigmodel.cn/api/paas/v4",
            global_upstream_key_env="GLM_API_KEY",
            master_key="sk-test",
            drop_params=True,
            streaming=True,
        )

        parsed = yaml.safe_load(config_text)
        assert parsed["model_list"][0]["model_name"] == "glm-4.6"
        assert parsed["model_list"][0]["litellm_params"]["model"] == "openai/glm-4.6"
        # Verify reasoning_effort is not present since GLM doesn't support it
        assert "reasoning_effort" not in parsed["model_list"][0]["litellm_params"]

    def test_glm_config_from_environment(self, monkeypatch):
        """Verify GLM can be configured via environment variables."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "glm")
        monkeypatch.setenv("MODEL_GLM_UPSTREAM_MODEL", "glm-4.6")
        monkeypatch.setenv("GLM_API_KEY", "sk-glm-test")

        specs = load_model_specs_from_env()
        assert len(specs) == 1
        assert specs[0].alias == "glm-4.6"
        assert specs[0].upstream_model == "glm-4.6"
        # GLM gets default reasoning_effort of "none" which will be filtered out during rendering
        assert specs[0].reasoning_effort == "none"

    def test_glm_reasoning_effort_filtered_in_config(self, monkeypatch):
        """Verify that reasoning_effort is filtered out for GLM-4.6 even if specified."""
        spec = make_spec(
            key="glm",
            alias="glm-4.6",
            upstream_model="glm-4.6",
            reasoning_effort="high",  # Should be filtered out
        )
        config_text = render_config(
            model_specs=[spec],
            global_upstream_base="https://open.bigmodel.cn/api/paas/v4",
            global_upstream_key_env="GLM_API_KEY",
            master_key="sk-test",
            drop_params=True,
            streaming=True,
        )

        parsed = yaml.safe_load(config_text)
        # Even though reasoning_effort was specified, it should be filtered out
        assert "reasoning_effort" not in parsed["model_list"][0]["litellm_params"]
