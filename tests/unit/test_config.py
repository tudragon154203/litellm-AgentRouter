#!/usr/bin/env python3
"""Comprehensive unit tests for config.py."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.config import (
    create_temp_config_if_needed,
    prepare_config,
    render_config,
)


class TestRenderConfigSimple:
    """Test cases for render_config function."""

    def test_render_config_minimal(self):
        """Test rendering a minimal config without optional parameters."""
        result = render_config(
            alias="test-model",
            upstream_model="gpt-4",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env=None,
            master_key=None,
            drop_params=True,
            streaming=True,
            reasoning_effort=None,
        )

        expected = """model_list:
  - model_name: "test-model"
    litellm_params:
      model: "openai/gpt-4"
      api_base: "https://api.openai.com/v1"
      api_key: null

litellm_settings:
  drop_params: true
  set_verbose: true
"""
        assert result == expected

    def test_render_config_streaming_enabled(self):
        """Test rendering config with streaming enabled."""
        result = render_config(
            alias="streaming-model",
            upstream_model="gpt-4",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env="OPENAI_API_KEY",
            master_key="sk-master-key",
            drop_params=True,
            streaming=True,
            reasoning_effort=None,
        )

        expected = """model_list:
  - model_name: "streaming-model"
    litellm_params:
      model: "openai/gpt-4"
      api_base: "https://api.openai.com/v1"
      api_key: "os.environ/OPENAI_API_KEY"

litellm_settings:
  drop_params: true
  set_verbose: true

general_settings:
  master_key: "sk-master-key"
"""
        assert result == expected

    def test_render_config_streaming_disabled(self):
        """Test rendering config with streaming disabled."""
        result = render_config(
            alias="non-streaming-model",
            upstream_model="gpt-3.5-turbo",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env="OPENAI_API_KEY",
            master_key=None,
            drop_params=False,
            streaming=False,
            reasoning_effort=None,
        )

        expected = """model_list:
  - model_name: "non-streaming-model"
    litellm_params:
      model: "openai/gpt-3.5-turbo"
      api_base: "https://api.openai.com/v1"
      api_key: "os.environ/OPENAI_API_KEY"

litellm_settings:
  drop_params: false
  set_verbose: false
"""
        assert result == expected

    def test_render_config_streaming_mixed_settings(self):
        """Test rendering config with mixed streaming and other settings."""
        result = render_config(
            alias="mixed-model",
            upstream_model="custom/model",
            upstream_base="https://custom.api.com/v1",
            upstream_key_env=None,
            master_key="sk-custom-master",
            drop_params=True,
            streaming=False,
        )

        expected = """model_list:
  - model_name: "mixed-model"
    litellm_params:
      model: "openai/custom/model"
      api_base: "https://custom.api.com/v1"
      api_key: null

litellm_settings:
  drop_params: true
  set_verbose: false

general_settings:
  master_key: "sk-custom-master"
"""
        assert result == expected


class TestPrepareConfigSimple:
    """Test cases for prepare_config function."""

    def test_prepare_config_with_nonexistent_file(self):
        """Test preparing config with nonexistent config file."""
        args = MagicMock()
        args.config = "/nonexistent/config.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            prepare_config(args)


class TestCreateTempConfigIfNeededSimple:
    """Test cases for create_temp_config_if_needed function."""

    def test_create_temp_config_with_existing_file(self):
        """Test using existing file when config is not generated."""
        config_path = Path("/existing/config.yaml")

        with create_temp_config_if_needed(config_path, False) as yielded_path:
            assert yielded_path == config_path

    def test_create_temp_config_with_generated_text(self):
        """Test creating temp config when config is generated text."""
        config_text = "model_list:\n  - model_name: test\n"

        with create_temp_config_if_needed(config_text, True) as config_path:
            assert config_path.exists()
            assert config_path.suffix == ".yaml"
            assert "litellm-config-" in config_path.name

            # Verify content was written
            content = config_path.read_text()
            assert content == config_text

        # File should be deleted after context
        assert not config_path.exists()

    def test_create_temp_config_with_path_and_true_generated(self):
        """Test path converted to string when is_generated is True."""
        # This tests the conversion behavior when path is provided but marked as generated
        config_path = Path("/existing/config.yaml")

        with create_temp_config_if_needed(str(config_path), True) as yielded_path:
            # Should create a temp file with the path content as text
            assert yielded_path.exists()
            assert yielded_path != config_path  # Should be different paths


class TestPrepareConfigExtended:
    """Extended test cases for prepare_config function to cover all lines."""

    def test_prepare_config_upstream_key_env_with_value(self, tmp_path):
        """Test prepare_config with upstream key env that has value."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = "API_KEY"
        args.master_key = None
        args.no_master_key = True
        args.drop_params = True
        args.print_config = False
        args.reasoning_effort = "medium"

        # Mock a valid config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("model_list: []")

        with patch.dict(os.environ, {"API_KEY": "sk-test-key"}):
            with patch("sys.exit"):  # Mock sys.exit to prevent actual exit
                config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert isinstance(config_data, str)

    def test_prepare_config_with_master_key_enabled(self):
        """Test prepare_config with master key enabled (not disabled)."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = "sk-custom-master"
        args.no_master_key = False
        args.drop_params = True
        args.print_config = False
        args.reasoning_effort = "medium"

        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.exit"):  # Mock sys.exit to prevent actual exit
                config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert "sk-custom-master" in config_data

    def test_prepare_config_missing_upstream_key_env_warning(self):
        """Test prepare_config warning for missing upstream key env (covers line 70)."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = "MISSING_API_KEY"  # This env var is not set
        args.master_key = None
        args.no_master_key = True
        args.drop_params = True
        args.print_config = False
        args.reasoning_effort = "medium"

        with patch.dict(os.environ, {}, clear=True):  # Ensure the env var is not set
            with patch("sys.exit"):  # Mock sys.exit to prevent actual exit
                with patch("builtins.print") as mock_print:
                    config_data, is_generated = prepare_config(args)

        assert is_generated is True
        # Verify warning was printed to stderr
        mock_print.assert_called_once()
        warning_msg = mock_print.call_args[0][0]
        assert "WARNING: Environment variable 'MISSING_API_KEY' is not set" in warning_msg
        assert "Upstream calls may fail authentication" in warning_msg

    def test_prepare_config_with_no_upstream_key_env(self):
        """Test prepare_config with no upstream key env set."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = None
        args.no_master_key = True
        args.drop_params = False
        args.print_config = False
        args.reasoning_effort = "medium"
        args.reasoning_effort = "medium"

        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.exit"):  # Mock sys.exit to prevent actual exit
                config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert "api_key: null" in config_data

    def test_prepare_config_with_drop_params_false(self):
        """Test prepare_config with drop_params disabled."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = None
        args.no_master_key = True
        args.drop_params = False
        args.print_config = False
        args.reasoning_effort = "medium"

        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.exit"):  # Mock sys.exit to prevent actual exit
                config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert "drop_params: false" in config_data

    def test_prepare_config_render_config_integration(self):
        """Test prepare_config integrates properly with render_config."""
        args = MagicMock()
        args.config = None
        args.alias = "test-alias"
        args.model = "gpt-3.5-turbo"
        args.upstream_base = "https://custom.api.com"
        args.upstream_key_env = "CUSTOM_KEY"
        args.master_key = "sk-master-123"
        args.no_master_key = False
        args.drop_params = True
        args.print_config = False
        args.reasoning_effort = "medium"

        with patch.dict(os.environ, {"CUSTOM_KEY": "sk-api-key"}):
            with patch("sys.exit"):  # Mock sys.exit to prevent actual exit
                config_data, is_generated = prepare_config(args)

        assert is_generated is True
        # Verify all components are in the generated config
        assert "test-alias" in config_data
        assert "gpt-3.5-turbo" in config_data
        assert "https://custom.api.com" in config_data
        assert "CUSTOM_KEY" in config_data
        assert "sk-master-123" in config_data
        assert "drop_params: true" in config_data

    def test_prepare_config_with_valid_existing_file(self, tmp_path):
        """Test prepare_config with a valid existing config file (covers line 66)."""
        args = MagicMock()
        args.config = str(tmp_path / "config.yaml")
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = None
        args.no_master_key = True
        args.drop_params = True
        args.print_config = False
        args.reasoning_effort = "medium"

        # Create a valid config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("model_list: []")

        config_data, is_generated = prepare_config(args)

        assert is_generated is False
        assert config_data == config_file

    def test_prepare_config_print_config_exits(self):
        """Test prepare_config with print_config flag (covers lines 86-87)."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = None
        args.no_master_key = True
        args.drop_params = True
        args.print_config = True
        args.reasoning_effort = "medium"

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                with patch("builtins.print") as mock_print:
                    prepare_config(args)

        assert exc_info.value.code == 0
        mock_print.assert_called_once()
        printed_config = mock_print.call_args[0][0]
        assert "model_list:" in printed_config
        assert "test-model" in printed_config


class TestRenderConfigEdgeCases:
    """Test edge cases and complex combinations for render_config."""

    def test_render_config_full_flag_combination(self):
        """Test rendering with many flags combined (from integration tests)."""
        result = render_config(
            alias="integration-test-model",
            upstream_model="gpt-5",
            upstream_base="https://custom.api.com/v1",
            upstream_key_env="CUSTOM_API_KEY",
            master_key="sk-custom-integration",
            drop_params=True,
            streaming=True,
        )
        config = yaml.safe_load(result)

        # Verify all components are present
        assert config["model_list"][0]["model_name"] == "integration-test-model"
        assert config["model_list"][0]["litellm_params"]["model"] == "openai/gpt-5"
        assert config["model_list"][0]["litellm_params"]["api_base"] == "https://custom.api.com/v1"
        assert config["model_list"][0]["litellm_params"]["api_key"] == "os.environ/CUSTOM_API_KEY"
        assert config["litellm_settings"]["drop_params"] is True
        assert config["litellm_settings"]["set_verbose"] is True

    def test_render_config_custom_model_aliases(self):
        """Test custom model alias edge cases (from integration tests)."""
        test_cases = [
            "custom-model",
            "my-gpt5",
            "work-assistant",
            "api-model-v1",
            "test-model_v2-with.special"  # Special characters
        ]

        for alias in test_cases:
            result = render_config(
                alias=alias,
                upstream_model="gpt-4",
                upstream_base="https://api.openai.com/v1",
                upstream_key_env=None,
                master_key=None,
                drop_params=True,
                streaming=False,
            )
            config = yaml.safe_load(result)
            assert config["model_list"][0]["model_name"] == alias

    def test_render_config_long_alias(self):
        """Test with very long alias (edge case from integration tests)."""
        long_alias = "a" * 100
        result = render_config(
            alias=long_alias,
            upstream_model="gpt-4",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env=None,
            master_key=None,
            drop_params=True,
            streaming=True,
        )
        config = yaml.safe_load(result)
        assert config["model_list"][0]["model_name"] == long_alias

    def test_render_config_environment_variable_references(self):
        """Test that environment variables are properly referenced in output."""
        result = render_config(
            alias="test-model",
            upstream_model="gpt-5",
            upstream_base="https://render-test.api.com/v1",
            upstream_key_env="CUSTOM_API_KEY",
            master_key=None,
            drop_params=True,
            streaming=False,
        )

        # Should reference environment variable in config
        assert "os.environ/CUSTOM_API_KEY" in result
        assert "gpt-5" in result
        assert "https://render-test.api.com/v1" in result
        assert "set_verbose: false" in result


class TestRenderConfigReasoningEffort:
    """Test cases for reasoning_effort parameter in render_config function."""

    def test_render_config_with_reasoning_effort_low(self):
        """Test rendering config with reasoning_effort='low'."""
        result = render_config(
            alias="reasoning-low-model",
            upstream_model="gpt-5",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env="OPENAI_API_KEY",
            master_key=None,
            drop_params=True,
            streaming=True,
            reasoning_effort="low",
        )

        expected = """model_list:
  - model_name: "reasoning-low-model"
    litellm_params:
      model: "openai/gpt-5"
      api_base: "https://api.openai.com/v1"
      api_key: "os.environ/OPENAI_API_KEY"
      reasoning_effort: "low"

litellm_settings:
  drop_params: true
  set_verbose: true
"""
        assert result == expected

    def test_render_config_with_reasoning_effort_medium(self):
        """Test rendering config with reasoning_effort='medium'."""
        result = render_config(
            alias="reasoning-medium-model",
            upstream_model="gpt-5",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env=None,
            master_key="sk-master",
            drop_params=False,
            streaming=False,
            reasoning_effort="medium",
        )

        expected = """model_list:
  - model_name: "reasoning-medium-model"
    litellm_params:
      model: "openai/gpt-5"
      api_base: "https://api.openai.com/v1"
      api_key: null
      reasoning_effort: "medium"

litellm_settings:
  drop_params: false
  set_verbose: false

general_settings:
  master_key: "sk-master"
"""
        assert result == expected

    def test_render_config_with_reasoning_effort_high(self):
        """Test rendering config with reasoning_effort='high'."""
        result = render_config(
            alias="reasoning-high-model",
            upstream_model="gpt-5",
            upstream_base="https://agentrouter.org/v1",
            upstream_key_env="AGENTROUTER_KEY",
            master_key=None,
            drop_params=True,
            streaming=True,
            reasoning_effort="high",
        )

        # Check that reasoning_effort is included
        assert 'reasoning_effort: "high"' in result
        assert "reasoning-high-model" in result
        assert "agentrouter.org" in result

    def test_render_config_with_reasoning_effort_none(self):
        """Test rendering config with reasoning_effort='none' (should not include parameter)."""
        result = render_config(
            alias="no-reasoning-model",
            upstream_model="gpt-4",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env=None,
            master_key=None,
            drop_params=True,
            streaming=True,
            reasoning_effort="none",
        )

        # Should NOT include reasoning_effort parameter
        assert "reasoning_effort" not in result
        assert "no-reasoning-model" in result

    def test_render_config_with_reasoning_effort_null(self):
        """Test rendering config with reasoning_effort=None (should not include parameter)."""
        result = render_config(
            alias="null-reasoning-model",
            upstream_model="gpt-4",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env=None,
            master_key=None,
            drop_params=True,
            streaming=True,
            reasoning_effort=None,
        )

        # Should NOT include reasoning_effort parameter
        assert "reasoning_effort" not in result
        assert "null-reasoning-model" in result

    def test_render_config_with_reasoning_effort_all_levels(self):
        """Test all reasoning_effort levels with yaml parsing."""
        effort_levels = ["low", "medium", "high"]

        for effort in effort_levels:
            result = render_config(
                alias=f"model-{effort}",
                upstream_model="gpt-5",
                upstream_base="https://api.openai.com/v1",
                upstream_key_env="API_KEY",
                master_key=None,
                drop_params=True,
                streaming=True,
                reasoning_effort=effort,
            )

            config = yaml.safe_load(result)

            # Verify reasoning_effort is correctly set in litellm_params
            assert config["model_list"][0]["litellm_params"]["reasoning_effort"] == effort
            assert config["model_list"][0]["model_name"] == f"model-{effort}"

    def test_render_config_reasoning_with_mixed_settings(self):
        """Test reasoning_effort with various other settings."""
        result = render_config(
            alias="mixed-reasoning-model",
            upstream_model="custom/gpt-5-reasoning",
            upstream_base="https://custom-reasoning.api.com/v1",
            upstream_key_env="CUSTOM_REASONING_KEY",
            master_key="sk-reasoning-master",
            drop_params=False,
            streaming=False,
            reasoning_effort="high",
        )

        config = yaml.safe_load(result)

        # Verify all settings are present
        assert config["model_list"][0]["model_name"] == "mixed-reasoning-model"
        assert config["model_list"][0]["litellm_params"]["model"] == "openai/custom/gpt-5-reasoning"
        assert config["model_list"][0]["litellm_params"]["api_base"] == "https://custom-reasoning.api.com/v1"
        assert config["model_list"][0]["litellm_params"]["api_key"] == "os.environ/CUSTOM_REASONING_KEY"
        assert config["model_list"][0]["litellm_params"]["reasoning_effort"] == "high"
        assert config["litellm_settings"]["drop_params"] is False
        assert config["litellm_settings"]["set_verbose"] is False
        assert config["general_settings"]["master_key"] == "sk-reasoning-master"
