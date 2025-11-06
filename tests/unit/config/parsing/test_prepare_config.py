#!/usr/bin/env python3
"""Unit tests for prepare_config function."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from src.config.models import ModelSpec
from src.config.parsing import prepare_config
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
        assert args.model_specs

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

    def test_prepare_config_missing_config_file(self):
        """Test error when config file doesn't exist."""
        from unittest.mock import MagicMock
        mock_args = MagicMock()
        mock_args.config = "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found: nonexistent.yaml"):
            prepare_config(mock_args)

    def test_prepare_config_with_missing_env_vars(self):
        """Test prepare_config with model specs having missing env vars."""
        from unittest.mock import MagicMock
        mock_args = MagicMock()
        mock_args.config = None
        mock_args.model_specs = [
            ModelSpec(
                key="test",
                alias="test-model",
                upstream_model="gpt-5",
                upstream_key_env="MISSING_API_KEY"
            )
        ]
        mock_args.no_master_key = False
        mock_args.master_key = "sk-local-master"
        mock_args.upstream_base = None
        mock_args.upstream_key_env = None
        mock_args.drop_params = True
        mock_args.streaming = True
        mock_args.print_config = False

        with patch('builtins.print') as mock_print:
            with patch.dict(os.environ, {}, clear=True):
                config_text, is_generated = prepare_config(mock_args)

                mock_print.assert_called()
                warning_call = str(mock_print.call_args[0][0])
                assert "WARNING: Environment variable 'MISSING_API_KEY'" in warning_call
                assert "for model 'test-model' is not set" in warning_call


class TestTemporaryConfig:
    """Tests for temporary config helper."""

    def test_create_temp_config_if_needed(self, tmp_path):
        """Generated config should be written to a temporary file."""
        config_text = "model_list:\n  - model_name: test\n"

        with create_temp_config_if_needed(config_text, True) as path:
            assert path.exists()
            assert path.read_text() == config_text

        assert not path.exists()

    def test_create_temp_config_with_existing_path(self):
        """Test when config_data is an existing path (not generated)."""
        from src.utils import temporary_config as create_temp_config_if_needed
        from unittest.mock import patch, MagicMock

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_file.__exit__.return_value = None
            mock_open.return_value = mock_file

            existing_path = Path("/tmp/test_config.yaml")

            with create_temp_config_if_needed(existing_path, False) as config_path:
                assert config_path == existing_path
                mock_open.assert_not_called()
