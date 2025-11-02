#!/usr/bin/env python3
"""Unit tests for src.config using the multi-model schema."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from src.config import (
    ModelSpec,
    create_temp_config_if_needed,
    load_model_specs_from_env,
    prepare_config,
    render_config,
)


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
        monkeypatch.setenv("OPENAI_API_BASE", "https://agentrouter.org/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        monkeypatch.setenv("MODEL_GPT5_ALIAS", "gpt-5")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("MODEL_GPT5_REASONING_EFFORT", "medium")

        monkeypatch.setenv("MODEL_DEEPSEEK_ALIAS", "deepseek-v3.2")
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
        monkeypatch.setenv("MODEL_PRIMARY_ALIAS", "primary")
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
        assert parsed["model_list"][0]["model_name"] == "primary"
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


class TestTemporaryConfig:
    """Tests for temporary config helper."""

    def test_create_temp_config_if_needed(self, tmp_path):
        """Generated config should be written to a temporary file."""
        config_text = "model_list:\n  - model_name: test\n"

        with create_temp_config_if_needed(config_text, True) as path:
            assert path.exists()
            assert path.read_text() == config_text

        assert not path.exists()
