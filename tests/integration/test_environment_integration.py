#!/usr/bin/env python3
"""Integration tests for environment variable functionality."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import yaml

from src.cli import parse_args
from src.config import render_config


class TestEnvironmentIntegration:
    """Integration tests for environment variable handling."""

    def test_config_rendering_with_environment_variables(self):
        """Test configuration rendering with environment variables."""
        env_vars = {
            "OPENAI_API_KEY": "sk-env-test-key",
            "LITELLM_MASTER_KEY": "sk-env-master",
            "OPENAI_MODEL": "gpt-5",
            "OPENAI_BASE_URL": "https://api.custom.com/v1"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([])  # Use defaults from environment

            master_key = None if args.no_master_key else args.master_key
            config_content = render_config(
                alias=args.alias,
                upstream_model=args.model,
                upstream_base=args.upstream_base,
                upstream_key_env=args.upstream_key_env,
                master_key=master_key,
                drop_params=args.drop_params
            )
            config = yaml.safe_load(config_content)

            assert config["model_list"][0]["model_name"] == "local-gpt"  # default alias
            assert config["model_list"][0]["litellm_params"]["model"] == "gpt-5"

    def test_environment_variable_precedence(self):
        """Test that environment variables are properly used as fallbacks."""
        # Set environment variables
        env_vars = {
            "OPENAI_API_KEY": "sk-env-key",
            "LITELLM_MASTER_KEY": "sk-env-master",
            "OPENAI_MODEL": "gpt-5",
            "LITELLM_HOST": "localhost",
            "LITELLM_PORT": "5000",
            "OPENAI_BASE_URL": "https://env.api.com/v1"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([])  # Should use environment defaults

            assert args.model == "gpt-5"
            assert args.host == "localhost"
            assert args.port == 5000
            assert args.upstream_base == "https://env.api.com/v1"
            assert args.master_key == "sk-env-master"
            assert args.upstream_key_env == "OPENAI_API_KEY"

    def test_cli_overrides_environment_variables(self):
        """Test that CLI arguments take precedence over environment variables."""
        env_vars = {
            "OPENAI_MODEL": "gpt-4",
            "LITELLM_HOST": "localhost",
            "LITELLM_PORT": "5000",
            "OPENAI_BASE_URL": "https://env.api.com/v1"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([
                "--model", "gpt-5",
                "--host", "127.0.0.1",
                "--port", "9000",
                "--upstream-base", "https://cli.api.com/v1"
            ])

            # CLI should override environment
            assert args.model == "gpt-5"  # CLI override
            assert args.host == "127.0.0.1"  # CLI override
            assert args.port == 9000  # CLI override
            assert args.upstream_base == "https://cli.api.com/v1"  # CLI override

    def test_missing_environment_variables_handled_gracefully(self):
        """Test that missing environment variables are handled gracefully."""
        # Clear all relevant environment variables
        env_vars = {}
        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([])  # Should use hardcoded defaults

            # Should fall back to defaults when env vars are missing
            assert args.model == "gpt-4o"  # Default in CLI
            assert args.host == "0.0.0.0"  # Default in CLI
            assert args.port == 4000  # Default in CLI
            assert args.upstream_base == "https://api.openai.com/v1"  # Default in CLI

    def test_partial_environment_variables(self):
        """Test partial environment variable configuration."""
        env_vars = {
            "OPENAI_MODEL": "gpt-5",
            "LITELLM_HOST": "custom-host"
            # Missing: LITELLM_PORT, OPENAI_BASE_URL, etc.
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([])

            # Should use env vars where available, defaults where missing
            assert args.model == "gpt-5"  # From env
            assert args.host == "custom-host"  # From env
            assert args.port == 4000  # From default
            assert args.upstream_base == "https://api.openai.com/v1"  # From default

    def test_environment_variable_config_rendering(self):
        """Test that environment variables are properly rendered in config."""
        env_vars = {
            "OPENAI_API_KEY": "sk-render-test",
            "OPENAI_MODEL": "gpt-5",
            "OPENAI_BASE_URL": "https://render-test.api.com/v1"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([])

            master_key = None if args.no_master_key else args.master_key
            config_content = render_config(
                alias=args.alias,
                upstream_model=args.model,
                upstream_base=args.upstream_base,
                upstream_key_env=args.upstream_key_env,
                master_key=master_key,
                drop_params=args.drop_params
            )

            # Should reference environment variable in config
            assert "os.environ/OPENAI_API_KEY" in config_content
            assert "gpt-5" in config_content
            assert "https://render-test.api.com/v1" in config_content

    def test_custom_environment_variable_names(self):
        """Test custom environment variable names for API key."""
        env_vars = {
            "CUSTOM_API_KEY": "sk-custom-env-key",
            "OPENAI_MODEL": "gpt-5"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([
                "--upstream-key-env", "CUSTOM_API_KEY"
            ])

            assert args.upstream_key_env == "CUSTOM_API_KEY"

            master_key = None if args.no_master_key else args.master_key
            config_content = render_config(
                alias=args.alias,
                upstream_model=args.model,
                upstream_base=args.upstream_base,
                upstream_key_env=args.upstream_key_env,
                master_key=master_key,
                drop_params=args.drop_params
            )

            # Should reference the custom environment variable
            assert "os.environ/CUSTOM_API_KEY" in config_content
            assert "os.environ/OPENAI_API_KEY" not in config_content