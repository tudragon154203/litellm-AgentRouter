#!/usr/bin/env python3
"""
Integration tests for Docker entrypoint module.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.config.entrypoint import main


@pytest.fixture(autouse=True)
def clear_model_env(monkeypatch):
    """Remove MODEL_* vars so tests can control the configuration surface."""
    for key in list(os.environ.keys()):
        if key.startswith("MODEL_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("PROXY_MODEL_KEYS", raising=False)


class TestEntrypointIntegration:
    """Integration tests for entrypoint with real environment variables."""

    @patch("src.config.entrypoint.os.execvp")
    def test_entrypoint_with_real_environment(self, mock_execvp, monkeypatch):
        """Test full entrypoint flow with real environment variables."""
        # Setup real environment
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("MODEL_GPT5_REASONING_EFFORT", "high")
        monkeypatch.setenv("MODEL_DEEPSEEK_UPSTREAM_MODEL", "deepseek-v3.2")
        monkeypatch.setenv("MODEL_DEEPSEEK_REASONING_EFFORT", "medium")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-1234567890")
        monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-local-master")
        monkeypatch.setenv("LITELLM_HOST", "0.0.0.0")
        monkeypatch.setenv("PORT", "4000")
        monkeypatch.setenv("NODE_UPSTREAM_PROXY_ENABLE", "0")  # Disable Node proxy for this test

        # Use a temporary file for config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name

        try:
            # Patch the config path to use our temp file
            with patch("src.config.entrypoint.write_config_file") as mock_write:
                # Capture the config text that would be written
                config_text = None

                def capture_config(text, path):
                    nonlocal config_text
                    config_text = text
                    # Actually write it to our temp file
                    with open(config_path, 'w') as f:
                        f.write(text)

                mock_write.side_effect = capture_config

                # Call main
                main()

                # Verify execvp was called
                assert mock_execvp.called

                # Verify config was written
                assert mock_write.called
                assert config_text is not None

                # Verify config file exists and is valid YAML
                assert Path(config_path).exists()
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)

                # Verify config structure
                assert "model_list" in config_data
                assert len(config_data["model_list"]) == 2

                model_lookup = {model["model_name"]: model for model in config_data["model_list"]}
                gpt5_model = model_lookup["gpt-5"]
                assert gpt5_model["model_name"] == "gpt-5"
                assert gpt5_model["litellm_params"]["model"] == "openai/gpt-5"
                assert gpt5_model["litellm_params"]["api_base"] == "https://agentrouter.org/v1"
                assert gpt5_model["litellm_params"]["api_key"] == "sk-test-key-1234567890"
                assert gpt5_model["litellm_params"]["reasoning_effort"] == "high"

                deepseek_model = model_lookup["deepseek-v3.2"]
                assert deepseek_model["model_name"] == "deepseek-v3.2"
                assert deepseek_model["litellm_params"]["model"] == "openai/deepseek-v3.2"
                assert deepseek_model["litellm_params"]["reasoning_effort"] == "medium"

                # Verify litellm_settings
                assert config_data["litellm_settings"]["drop_params"] is True
                assert config_data["litellm_settings"]["set_verbose"] is False

                # Verify general_settings
                assert config_data["general_settings"]["master_key"] == "sk-local-master"

        finally:
            # Clean up temp file
            try:
                Path(config_path).unlink()
            except Exception:
                pass

    @patch("src.config.entrypoint.os.execvp")
    def test_entrypoint_generates_valid_yaml(self, mock_execvp, monkeypatch):
        """Test that generated config is valid YAML."""
        # Setup minimal environment
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-local-master")

        # Use a temporary file for config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name

        try:
            # Patch the config path
            with patch("src.config.entrypoint.write_config_file") as mock_write:
                config_text = None

                def capture_config(text, path):
                    nonlocal config_text
                    config_text = text
                    with open(config_path, 'w') as f:
                        f.write(text)

                mock_write.side_effect = capture_config

                # Call main
                main()

                # Verify config is valid YAML
                assert config_text is not None
                config_data = yaml.safe_load(config_text)
                assert isinstance(config_data, dict)
                assert "model_list" in config_data

        finally:
            try:
                Path(config_path).unlink()
            except Exception:
                pass

    @patch("src.config.entrypoint.os.execvp")
    def test_entrypoint_config_matches_expected_structure(self, mock_execvp, monkeypatch):
        """Test that generated config matches expected structure."""
        # Setup environment
        monkeypatch.setenv("MODEL_TESTMODEL_UPSTREAM_MODEL", "test-upstream")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://test.example.com/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-test-master")

        # Use a temporary file for config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name

        try:
            with patch("src.config.entrypoint.write_config_file") as mock_write:
                config_text = None

                def capture_config(text, path):
                    nonlocal config_text
                    config_text = text
                    with open(config_path, 'w') as f:
                        f.write(text)

                mock_write.side_effect = capture_config

                # Call main
                main()

                # Parse config
                config_data = yaml.safe_load(config_text)

                # Verify required top-level keys
                assert "model_list" in config_data
                assert "litellm_settings" in config_data
                assert "general_settings" in config_data

                # Verify model_list structure
                assert isinstance(config_data["model_list"], list)
                assert len(config_data["model_list"]) > 0

                model = config_data["model_list"][0]
                assert "model_name" in model
                assert "litellm_params" in model

                # Verify litellm_params structure
                params = model["litellm_params"]
                assert "model" in params
                assert "api_base" in params
                assert "custom_llm_provider" in params
                assert "headers" in params

                # Verify headers
                headers = params["headers"]
                assert "User-Agent" in headers
                assert "Content-Type" in headers

                # Verify litellm_settings
                assert "drop_params" in config_data["litellm_settings"]
                assert "set_verbose" in config_data["litellm_settings"]

                # Verify general_settings
                assert "master_key" in config_data["general_settings"]

        finally:
            try:
                Path(config_path).unlink()
            except Exception:
                pass
