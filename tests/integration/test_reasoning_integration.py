#!/usr/bin/env python3
"""Integration-style tests validating reasoning_effort behaviour."""

from __future__ import annotations

import os
import subprocess
from types import SimpleNamespace

import pytest
import yaml

from src.config.models import ModelSpec
from src.config.parsing import prepare_config
from src.config.rendering import render_config


def run_main_with_env(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Helper to invoke `python -m src.main --print-config` with env."""
    process = subprocess.run(
        ["python", "-m", "src.main", "--print-config"],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
    )
    return process


class TestReasoningEffortEndToEnd:
    """End-to-end scenarios for reasoning handling."""

    def test_env_driven_reasoning(self, monkeypatch):
        """Environment configuration should include reasoning for GPT-5 only."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "gpt5,deepseek")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("MODEL_GPT5_REASONING_EFFORT", "high")
        monkeypatch.setenv("MODEL_DEEPSEEK_UPSTREAM_MODEL", "deepseek-v3.2")
        monkeypatch.setenv("MODEL_DEEPSEEK_REASONING_EFFORT", "low")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("SKIP_PREREQ_CHECK", "1")

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

        config_text, _ = prepare_config(args)
        parsed = yaml.safe_load(config_text)
        gpt5_params = parsed["model_list"][0]["litellm_params"]
        deepseek_params = parsed["model_list"][1]["litellm_params"]

        assert gpt5_params["reasoning_effort"] == "high"
        assert deepseek_params["reasoning_effort"] == "low"

    def test_env_reasoning_none_omits_value(self, monkeypatch):
        """Setting reasoning to 'none' should omit the parameter."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "deepseek")
        monkeypatch.setenv("MODEL_DEEPSEEK_UPSTREAM_MODEL", "deepseek-v3.2")
        monkeypatch.setenv("MODEL_DEEPSEEK_REASONING_EFFORT", "none")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("SKIP_PREREQ_CHECK", "1")

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

        config_text, _ = prepare_config(args)
        parsed = yaml.safe_load(config_text)
        deepseek_params = parsed["model_list"][0]["litellm_params"]
        assert "reasoning_effort" not in deepseek_params

    def test_cli_reasoning_overrides(self, monkeypatch):
        """CLI-provided reasoning should override env defaults."""
        monkeypatch.setenv("SKIP_PREREQ_CHECK", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        process = subprocess.run(
            [
                "python",
                "-m",
                "src.main",
                "--model-spec",
                "key=gpt5,alias=gpt-5,upstream=gpt-5,reasoning=low",
                "--model-spec",
                "key=deepseek,alias=deepseek-v3.2,upstream=deepseek-v3.2,reasoning=none",
                "--print-config",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "SKIP_PREREQ_CHECK": "1"},
        )

        assert process.returncode == 0
        parsed = yaml.safe_load(process.stdout)
        assert parsed["model_list"][0]["litellm_params"]["reasoning_effort"] == "low"
        assert "reasoning_effort" not in parsed["model_list"][1]["litellm_params"]

    def test_missing_reasoning_defaults_to_none(self, monkeypatch):
        """Omitting reasoning should leave the field absent."""
        monkeypatch.setenv("PROXY_MODEL_KEYS", "primary")
        monkeypatch.setenv("MODEL_PRIMARY_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("SKIP_PREREQ_CHECK", "1")

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

        config_text, _ = prepare_config(args)
        parsed = yaml.safe_load(config_text)
        assert "reasoning_effort" not in parsed["model_list"][0]["litellm_params"]


class TestRenderConfigIntegration:
    """Direct render_config use-cases."""

    def test_render_config_multiple_models(self):
        """Rendered YAML should include both models with correct data."""
        specs = [
            ModelSpec(
                key="gpt5",
                alias="gpt-5",
                upstream_model="gpt-5",
                reasoning_effort="medium",
            ),
            ModelSpec(
                key="deepseek",
                alias="deepseek-v3.2",
                upstream_model="deepseek-v3.2",
                reasoning_effort="none",
            ),
        ]
        config_text = render_config(
            model_specs=specs,
            global_upstream_base="https://agentrouter.org/v1",
            global_upstream_key_env="OPENAI_API_KEY",
            master_key=None,
            drop_params=True,
            streaming=True,
        )
        parsed = yaml.safe_load(config_text)
        assert len(parsed["model_list"]) == 2
        assert parsed["model_list"][0]["litellm_params"]["reasoning_effort"] == "medium"
        assert "reasoning_effort" not in parsed["model_list"][1]["litellm_params"]

    def test_render_config_requires_specs(self):
        """Calling render_config without specs should raise ValueError."""
        with pytest.raises(ValueError):
            render_config(
                model_specs=[],
                global_upstream_base="https://agentrouter.org/v1",
                global_upstream_key_env="OPENAI_API_KEY",
                master_key=None,
                drop_params=True,
                streaming=True,
            )
