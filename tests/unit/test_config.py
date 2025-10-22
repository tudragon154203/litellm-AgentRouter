#!/usr/bin/env python3
"""Unit tests for config.py."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import (
    create_temp_config_if_needed,
    prepare_config,
    render_config,
)


class TestRenderConfig:
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
        )

        expected = """model_list:
  - model_name: "test-model"
    litellm_params:
      model: "gpt-4"
      api_base: "https://api.openai.com/v1"
      api_key: null

litellm_settings:
  drop_params: true
"""
        assert result == expected

    def test_render_config_with_api_key(self):
        """Test rendering config with API key environment variable."""
        result = render_config(
            alias="test-model",
            upstream_model="gpt-4",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env="OPENAI_API_KEY",
            master_key=None,
            drop_params=False,
        )

        expected = """model_list:
  - model_name: "test-model"
    litellm_params:
      model: "gpt-4"
      api_base: "https://api.openai.com/v1"
      api_key: "os.environ/OPENAI_API_KEY"

litellm_settings:
  drop_params: false
"""
        assert result == expected

    def test_render_config_with_master_key(self):
        """Test rendering config with master key."""
        result = render_config(
            alias="test-model",
            upstream_model="gpt-4",
            upstream_base="https://api.openai.com/v1",
            upstream_key_env="API_KEY",
            master_key="sk-master-key",
            drop_params=True,
        )

        expected = """model_list:
  - model_name: "test-model"
    litellm_params:
      model: "gpt-4"
      api_base: "https://api.openai.com/v1"
      api_key: "os.environ/API_KEY"

litellm_settings:
  drop_params: true

general_settings:
  master_key: "sk-master-key"
"""
        assert result == expected

    def test_render_config_with_special_characters(self):
        """Test rendering config with special characters that need escaping."""
        result = render_config(
            alias="model-with-\"quotes\"",
            upstream_model="model\\with\\backslashes",
            upstream_base="https://api.example.com/v1",
            upstream_key_env=None,
            master_key=None,
            drop_params=True,
        )

        # Should properly escape special characters
        assert '"model-with-\\"quotes\\""' in result
        assert '"model\\\\with\\\\backslashes"' in result

    def test_render_config_all_parameters(self):
        """Test rendering config with all parameters."""
        result = render_config(
            alias="full-model",
            upstream_model="gpt-4-turbo",
            upstream_base="https://custom.api.com/v1",
            upstream_key_env="CUSTOM_API_KEY",
            master_key="sk-custom-master",
            drop_params=False,
        )

        # Verify all components are present
        assert "model_name: \"full-model\"" in result
        assert "model: \"gpt-4-turbo\"" in result
        assert "api_base: \"https://custom.api.com/v1\"" in result
        assert "api_key: \"os.environ/CUSTOM_API_KEY\"" in result
        assert "drop_params: false" in result
        assert "master_key: \"sk-custom-master\"" in result


class TestPrepareConfig:
    """Test cases for prepare_config function."""

    def test_prepare_config_with_existing_file(self, tmp_path):
        """Test preparing config with existing config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("existing: config")

        args = MagicMock()
        args.config = str(config_file)

        config_data, is_generated = prepare_config(args)

        assert is_generated is False
        assert config_data == config_file

    def test_prepare_config_with_nonexistent_file(self):
        """Test preparing config with nonexistent config file."""
        args = MagicMock()
        args.config = "/nonexistent/config.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            prepare_config(args)

    def test_prepare_config_generate_minimal(self):
        """Test generating minimal config from args."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = None
        args.drop_params = True
        args.no_master_key = True
        args.print_config = False

        config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert isinstance(config_data, str)
        assert "model_name: \"test-model\"" in config_data
        assert "model: \"gpt-4\"" in config_data
        assert "api_key: null" in config_data

    def test_prepare_config_with_master_key_not_disabled(self):
        """Test generating config when master key is not disabled."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = "sk-master"
        args.no_master_key = False
        args.drop_params = True
        args.print_config = False

        config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert "master_key: \"sk-master\"" in config_data

    def test_prepare_config_with_master_key_disabled(self):
        """Test generating config when master key is disabled."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = "sk-master"  # This should be ignored
        args.no_master_key = True
        args.drop_params = True
        args.print_config = False

        config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert "master_key" not in config_data

    def test_prepare_config_upstream_key_env_warning(self, capsys):
        """Test warning when upstream key environment variable is not set."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = "NONEXISTENT_VAR"
        args.master_key = None
        args.no_master_key = True
        args.drop_params = True
        args.print_config = False

        with patch.dict(os.environ, {}, clear=True):
            config_data, is_generated = prepare_config(args)

        captured = capsys.readouterr()
        assert "WARNING: Environment variable 'NONEXISTENT_VAR' is not set" in captured.err
        assert is_generated is True

    def test_prepare_config_upstream_key_env_no_warning_when_set(self, capsys):
        """Test no warning when upstream key environment variable is set."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = "OPENAI_API_KEY"
        args.master_key = None
        args.no_master_key = True
        args.drop_params = True
        args.print_config = False

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            config_data, is_generated = prepare_config(args)

        captured = capsys.readouterr()
        assert "WARNING" not in captured.err
        assert is_generated is True

    def test_prepare_config_upstream_key_env_none_uses_default(self):
        """Test that None upstream_key_env results in no API key in config."""
        args = MagicMock()
        args.config = None
        args.alias = "test-model"
        args.model = "gpt-4"
        args.upstream_base = "https://api.openai.com/v1"
        args.upstream_key_env = None
        args.master_key = None
        args.no_master_key = True
        args.drop_params = True
        args.print_config = False

        config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert "api_key: null" in config_data

    def test_prepare_config_print_config_exits(self):
        """Test that print_config option prints config and exits."""
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

        with pytest.raises(SystemExit) as exc_info:
            with patch("builtins.print") as mock_print:
                prepare_config(args)

        assert exc_info.value.code == 0
        mock_print.assert_called_once()
        printed_config = mock_print.call_args[0][0]
        assert "model_name: \"test-model\"" in printed_config


class TestCreateTempConfigIfNeeded:
    """Test cases for create_temp_config_if_needed function."""

    def test_create_temp_config_with_generated_text(self):
        """Test creating temp config when config is generated text."""
        config_text = "model_list:\n  - model_name: test\n"

        with patch("src.utils.temporary_config") as mock_temp_config:
            mock_temp_path = MagicMock()
            mock_temp_config.return_value.__enter__.return_value = mock_temp_path

            with create_temp_config_if_needed(config_text, True) as config_path:
                assert config_path == mock_temp_path
                mock_temp_config.assert_called_once_with(config_text)

    def test_create_temp_config_with_existing_file(self):
        """Test using existing file when config is not generated."""
        config_path = Path("/existing/config.yaml")

        with create_temp_config_if_needed(config_path, False) as yielded_path:
            assert yielded_path == config_path

    def test_create_temp_config_context_manager_behavior(self):
        """Test that the context manager behaves correctly."""
        config_text = "test: config"

        with patch("src.utils.temporary_config") as mock_temp_config:
            mock_context = MagicMock()
            mock_temp_config.return_value = mock_context
            mock_temp_path = Path("/tmp/config.yaml")
            mock_context.__enter__.return_value = mock_temp_path

            with create_temp_config_if_needed(config_text, True) as config_path:
                assert config_path == mock_temp_path
                mock_context.__enter__.assert_called_once()

            mock_context.__exit__.assert_called_once()

    def test_create_temp_config_with_path_and_true_generated(self):
        """Test error case where path is provided but is_generated is True."""
        # This is an inconsistent state that shouldn't happen in normal usage
        config_path = Path("/existing/config.yaml")

        with patch("src.utils.temporary_config") as mock_temp_config:
            mock_temp_path = MagicMock()
            mock_temp_config.return_value.__enter__.return_value = mock_temp_path

            with create_temp_config_if_needed(config_path, True) as yielded_path:
                # Should treat it as generated text, converting to string
                mock_temp_config.assert_called_once_with(str(config_path))
                assert yielded_path == mock_temp_path