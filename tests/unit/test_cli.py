#!/usr/bin/env python3
"""Unit tests for cli.py."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli import parse_args


class TestParseArgs:
    """Test cases for parse_args function."""

    def test_parse_args_default_values(self):
        """Test parse_args with default values (no arguments)."""
        with patch.dict(os.environ, {}, clear=True):
            args = parse_args([])

            assert args.config is None
            assert args.alias == "gpt-5"
            assert args.model == "gpt-4o"
            assert args.upstream_base == "https://api.openai.com/v1"
            assert args.upstream_key_env == "OPENAI_API_KEY"
            assert args.master_key == "sk-local-master"
            assert args.host == "0.0.0.0"
            assert args.port == 4000
            assert args.workers == 1
            assert args.debug is False
            assert args.detailed_debug is False
            assert args.no_master_key is False
            assert args.drop_params is True
            assert args.print_config is False

    def test_parse_args_with_all_arguments(self):
        """Test parse_args with all command line arguments provided."""
        argv = [
            "--config", "/path/to/config.yaml",
            "--alias", "custom-model",
            "--model", "gpt-3.5-turbo",
            "--upstream-base", "https://custom.api.com/v1",
            "--upstream-key-env", "CUSTOM_API_KEY",
            "--master-key", "sk-custom-master",
            "--host", "127.0.0.1",
            "--port", "8080",
            "--workers", "4",
            "--debug",
            "--detailed-debug",
            "--no-master-key",
            "--no-drop-params",
            "--print-config",
        ]

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args(argv)

            assert args.config == Path("/path/to/config.yaml")
            assert args.alias == "custom-model"
            assert args.model == "gpt-3.5-turbo"
            assert args.upstream_base == "https://custom.api.com/v1"
            assert args.upstream_key_env == "CUSTOM_API_KEY"
            assert args.master_key == "sk-custom-master"
            assert args.host == "127.0.0.1"
            assert args.port == 8080
            assert args.workers == 4
            assert args.debug is True
            assert args.detailed_debug is True
            assert args.no_master_key is True
            assert args.drop_params is False
            assert args.print_config is True

    def test_parse_args_config_from_env(self):
        """Test parse_args with config from environment variable."""
        with patch.dict(os.environ, {"LITELLM_CONFIG": "/env/config.yaml"}):
            args = parse_args([])

            assert args.config == Path("/env/config.yaml")

    def test_parse_args_alias_from_env(self):
        """Test parse_args with alias from environment variable."""
        with patch.dict(os.environ, {"LITELLM_MODEL_ALIAS": "env-model"}):
            args = parse_args([])

            assert args.alias == "env-model"

    def test_parse_args_model_from_env(self):
        """Test parse_args with model from environment variable."""
        with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-3.5-turbo"}):
            args = parse_args([])

            assert args.model == "gpt-3.5-turbo"

    def test_parse_args_upstream_base_from_env(self):
        """Test parse_args with upstream base from environment variable."""
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://env.api.com/v1"}):
            args = parse_args([])

            assert args.upstream_base == "https://env.api.com/v1"


    def test_parse_args_master_key_from_env(self):
        """Test parse_args with master key from environment variable."""
        with patch.dict(os.environ, {"LITELLM_MASTER_KEY": "sk-env-master"}):
            args = parse_args([])

            assert args.master_key == "sk-env-master"

    def test_parse_args_host_from_env(self):
        """Test parse_args with host from environment variable."""
        with patch.dict(os.environ, {"LITELLM_HOST": "127.0.0.1"}):
            args = parse_args([])

            assert args.host == "127.0.0.1"

    def test_parse_args_port_from_env(self):
        """Test parse_args with port from environment variable."""
        with patch.dict(os.environ, {"LITELLM_PORT": "8080"}):
            args = parse_args([])

            assert args.port == 8080

    def test_parse_args_workers_from_env(self):
        """Test parse_args with workers from environment variable."""
        with patch.dict(os.environ, {"LITELLM_WORKERS": "4"}):
            args = parse_args([])

            assert args.workers == 4

    def test_parse_args_debug_from_env_true(self):
        """Test parse_args with debug from environment variable (true)."""
        with patch.dict(os.environ, {"LITELLM_DEBUG": "1"}):
            args = parse_args([])

            assert args.debug is True

    def test_parse_args_debug_from_env_false(self):
        """Test parse_args with debug from environment variable (false)."""
        with patch.dict(os.environ, {"LITELLM_DEBUG": "0"}):
            args = parse_args([])

            assert args.debug is False

    def test_parse_args_detailed_debug_from_env(self):
        """Test parse_args with detailed debug from environment variable."""
        with patch.dict(os.environ, {"LITELLM_DETAILED_DEBUG": "true"}):
            args = parse_args([])

            assert args.detailed_debug is True

    def test_parse_args_drop_params_from_env_true(self):
        """Test parse_args with drop_params from environment variable (true)."""
        with patch.dict(os.environ, {"LITELLM_DROP_PARAMS": "yes"}):
            args = parse_args([])

            assert args.drop_params is True

    def test_parse_args_drop_params_from_env_false(self):
        """Test parse_args with drop_params from environment variable (false)."""
        with patch.dict(os.environ, {"LITELLM_DROP_PARAMS": "no"}):
            args = parse_args([])

            assert args.drop_params is False

    def test_parse_args_cli_overrides_env(self):
        """Test that CLI arguments override environment variables."""
        env_vars = {
            "LITELLM_CONFIG": "/env/config.yaml",
            "LITELLM_MODEL_ALIAS": "env-model",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "OPENAI_BASE_URL": "https://env.api.com/v1",
            "LITELLM_MASTER_KEY": "sk-env-master",
            "LITELLM_HOST": "127.0.0.1",
            "LITELLM_PORT": "8080",
            "LITELLM_WORKERS": "4",
            "LITELLM_DEBUG": "1",
            "LITELLM_DETAILED_DEBUG": "1",
            "LITELLM_DROP_PARAMS": "no",
        }

        argv = [
            "--config", "/cli/config.yaml",
            "--alias", "cli-model",
            "--model", "gpt-4",
            "--upstream-base", "https://cli.api.com/v1",
            "--upstream-key-env", "CLI_API_KEY",
            "--master-key", "sk-cli-master",
            "--host", "localhost",
            "--port", "9000",
            "--workers", "2",
            "--no-drop-params",
        ]

        with patch.dict(os.environ, env_vars):
            args = parse_args(argv)

            # CLI arguments should take precedence
            assert args.config == Path("/cli/config.yaml")
            assert args.alias == "cli-model"
            assert args.model == "gpt-4"
            assert args.upstream_base == "https://cli.api.com/v1"
            assert args.upstream_key_env == "CLI_API_KEY"
            assert args.master_key == "sk-cli-master"
            assert args.host == "localhost"
            assert args.port == 9000
            assert args.workers == 2
            assert args.drop_params is False  # overridden by --no-drop-params

            # These should still come from env since not overridden
            assert args.debug is True
            assert args.detailed_debug is True

    def test_parse_args_upstream_key_env_empty_string(self):
        """Test parse_args with empty string for upstream_key_env."""
        argv = ["--upstream-key-env", ""]

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args(argv)

            assert args.upstream_key_env == ""

    def test_parse_args_no_drop_params_flag(self):
        """Test --no-drop-params flag behavior."""
        argv = ["--no-drop-params"]

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args(argv)

            assert args.drop_params is False

    def test_parse_args_drop_params_flag_overrides_env(self):
        """Test --drop-params flag overrides environment variable."""
        env_vars = {"LITELLM_DROP_PARAMS": "no"}
        argv = ["--drop-params"]

        with patch.dict(os.environ, env_vars):
            args = parse_args(argv)

            assert args.drop_params is True

    def test_parse_args_no_master_key_flag(self):
        """Test --no-master-key flag behavior."""
        argv = ["--no-master-key"]

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args(argv)

            assert args.no_master_key is True

    def test_parse_args_print_config_flag(self):
        """Test --print-config flag behavior."""
        argv = ["--print-config"]

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args(argv)

            assert args.print_config is True

    def test_parse_args_debug_and_detailed_debug_flags(self):
        """Test --debug and --detailed-debug flags."""
        argv = ["--debug", "--detailed-debug"]

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args(argv)

            assert args.debug is True
            assert args.detailed_debug is True

    def test_parse_args_with_none_argv(self):
        """Test parse_args with None as argv (should use sys.argv)."""
        # This tests the default behavior when no argv is provided
        with patch("sys.argv", ["script", "--alias", "test-model"]):
            with patch.dict(os.environ, {}, clear=True):
                args = parse_args(None)
                assert args.alias == "test-model"

    def test_parse_args_help_message(self):
        """Test that help message contains expected content."""
        with patch("sys.argv", ["script", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                parse_args(["--help"])

        assert exc_info.value.code == 0

    def test_parse_args_invalid_port(self):
        """Test parse_args with invalid port value."""
        with pytest.raises(SystemExit):
            with patch.dict(os.environ, {}, clear=True):
                parse_args(["--port", "invalid"])

    def test_parse_args_invalid_workers(self):
        """Test parse_args with invalid workers value."""
        with pytest.raises(SystemExit):
            with patch.dict(os.environ, {}, clear=True):
                parse_args(["--workers", "invalid"])

    def test_parse_args_mixed_case_booleans(self):
        """Test parse_args with various boolean string formats in env."""
        test_cases = [
            ("1", True),
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
            ("Yes", True),
            ("YES", True),
            ("on", True),
            ("On", True),
            ("ON", True),
            ("0", False),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("no", False),
            ("No", False),
            ("NO", False),
            ("off", False),
            ("Off", False),
            ("OFF", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"LITELLM_DEBUG": env_value}):
                args = parse_args([])
                assert args.debug is expected, f"Failed for env value: {env_value}"