#!/usr/bin/env python3
"""Unit tests for render_config function."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml

from src.config.models import ModelSpec
from src.config.rendering import render_config


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

    def test_render_config_with_no_api_key(self):
        """Test rendering config when no upstream key env is specified."""
        model_spec = ModelSpec(
            key="test",
            alias="test-model",
            upstream_model="gpt-5",
            upstream_key_env=None
        )

        config_text = render_config(
            model_specs=[model_spec],
            global_upstream_base="https://api.openai.com",
            global_upstream_key_env=None,
            master_key="sk-test",
            drop_params=True,
            streaming=True
        )

        assert "api_key: null" in config_text

    def test_render_config_with_reasoning_unsupported_model(self):
        """Test rendering config with reasoning effort for unsupported model."""
        with patch('src.config.models.get_model_capabilities') as mock_caps:
            mock_caps.return_value = {"supports_reasoning": False}

            model_spec = ModelSpec(
                key="test",
                alias="test-model",
                upstream_model="unsupported-model",
                reasoning_effort="high"
            )

            with patch('builtins.print') as mock_print:
                render_config(
                    model_specs=[model_spec],
                    global_upstream_base="https://api.openai.com",
                    global_upstream_key_env="API_KEY",
                    master_key="sk-test",
                    drop_params=True,
                    streaming=True
                )

                mock_print.assert_called()
                warning_call = str(mock_print.call_args[0][0])
                assert "WARNING: Model unsupported-model does not support reasoning_effort" in warning_call
                assert "ignoring reasoning_effort=high" in warning_call

    def test_render_config_empty_model_specs(self):
        """render_config should raise ValueError for empty model specs."""
        with pytest.raises(ValueError, match="No model specifications provided"):
            render_config(
                model_specs=[],
                global_upstream_base="https://api.openai.com/v1",
                global_upstream_key_env="OPENAI_API_KEY",
                master_key="sk-test",
                drop_params=False,
                streaming=True
            )

    def test_render_config_none_model_specs(self):
        """render_config should raise ValueError for None model specs."""
        with pytest.raises(ValueError, match="No model specifications provided"):
            render_config(
                model_specs=None,
                global_upstream_base="https://api.openai.com/v1",
                global_upstream_key_env="OPENAI_API_KEY",
                master_key="sk-test",
                drop_params=False,
                streaming=True
            )

    def test_render_model_with_custom_upstream(self):
        """Test rendering model with custom upstream (api_base and api_key included)."""
        spec = make_spec(
            key="gpt5",
            alias="gpt-5",
            upstream_model="gpt-5",
            upstream_base="https://custom.api.com/v1",
            upstream_key_env="CUSTOM_API_KEY"
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
        model_params = parsed["model_list"][0]["litellm_params"]
        assert model_params["api_base"] == "https://custom.api.com/v1"
        assert model_params["api_key"] == "os.environ/CUSTOM_API_KEY"

    def test_render_model_with_global_defaults(self):
        """Test rendering model with global defaults (api_base and api_key included)."""
        spec = make_spec(
            key="gpt5",
            alias="gpt-5",
            upstream_model="gpt-5"
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
        model_params = parsed["model_list"][0]["litellm_params"]
        assert model_params["api_base"] == "https://agentrouter.org/v1"
        assert model_params["api_key"] == "os.environ/OPENAI_API_KEY"

    def test_render_multiple_models_with_different_upstreams(self):
        """Test rendering multiple models with different upstreams."""
        specs = [
            make_spec(
                key="gpt5",
                alias="gpt-5",
                upstream_model="gpt-5",
                upstream_base="https://agentrouter.org/v1",
                upstream_key_env="AGENTROUTER_API_KEY"
            ),
            make_spec(
                key="claude",
                alias="claude-4.5-sonnet",
                upstream_model="claude-4.5-sonnet",
                upstream_base="https://api.hubs.com/v1",
                upstream_key_env="HUBS_API_KEY"
            ),
        ]

        config_text = render_config(
            model_specs=specs,
            global_upstream_base="https://default.com/v1",
            global_upstream_key_env="DEFAULT_KEY",
            master_key="sk-master",
            drop_params=True,
            streaming=True,
        )

        parsed = yaml.safe_load(config_text)
        assert len(parsed["model_list"]) == 2

        # First model
        model1_params = parsed["model_list"][0]["litellm_params"]
        assert model1_params["api_base"] == "https://agentrouter.org/v1"
        assert model1_params["api_key"] == "os.environ/AGENTROUTER_API_KEY"

        # Second model
        model2_params = parsed["model_list"][1]["litellm_params"]
        assert model2_params["api_base"] == "https://api.hubs.com/v1"
        assert model2_params["api_key"] == "os.environ/HUBS_API_KEY"

    def test_verify_yaml_structure_matches_expected_format(self):
        """Verify YAML structure matches expected format for multi-upstream."""
        spec = make_spec(
            key="gpt5",
            alias="gpt-5",
            upstream_model="gpt-5",
            upstream_base="https://agentrouter.org/v1",
            upstream_key_env="AGENTROUTER_API_KEY"
        )

        config_text = render_config(
            model_specs=[spec],
            global_upstream_base="https://default.com/v1",
            global_upstream_key_env="DEFAULT_KEY",
            master_key="sk-master",
            drop_params=True,
            streaming=True,
        )

        parsed = yaml.safe_load(config_text)

        # Verify structure
        assert "model_list" in parsed
        assert "litellm_settings" in parsed
        assert "general_settings" in parsed

        model_entry = parsed["model_list"][0]
        assert "model_name" in model_entry
        assert "litellm_params" in model_entry

        params = model_entry["litellm_params"]
        assert "model" in params
        assert "api_base" in params
        assert "api_key" in params
        assert "custom_llm_provider" in params
        assert "headers" in params
