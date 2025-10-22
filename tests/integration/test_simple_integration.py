#!/usr/bin/env python3
"""Simple integration tests for the LiteLLM proxy launcher."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli import parse_args
from src.config import render_config


class TestSimpleIntegration:
    """Simple integration tests that verify core functionality."""

    def test_gpt5_model_configuration(self):
        """Test GPT-5 model configuration integration."""
        args = parse_args([
            "--alias", "gpt5-test",
            "--model", "gpt-5",
            "--upstream-base", "https://api.openai.com/v1",
            "--upstream-key-env", "OPENAI_API_KEY"
        ])

        master_key = None if args.no_master_key else args.master_key
        config_content = render_config(
            alias=args.alias,
            upstream_model=args.model,
            upstream_base=args.upstream_base,
            upstream_key_env=args.upstream_key_env,
            master_key=master_key,
            drop_params=args.drop_params
        )

        assert "gpt5-test" in config_content
        assert "gpt-5" in config_content
        assert "https://api.openai.com/v1" in config_content
        assert "os.environ/OPENAI_API_KEY" in config_content

    def test_environment_variable_integration(self):
        """Test environment variable integration."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test-key",
            "OPENAI_MODEL": "gpt-5",
            "LITELLM_HOST": "localhost",
            "LITELLM_PORT": "5000"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([])

            assert args.model == "gpt-5"
            assert args.host == "localhost"
            assert args.port == 5000

            master_key = None if args.no_master_key else args.master_key
            config_content = render_config(
                alias=args.alias,
                upstream_model=args.model,
                upstream_base=args.upstream_base,
                upstream_key_env=args.upstream_key_env,
                master_key=master_key,
                drop_params=args.drop_params
            )

            assert "gpt-5" in config_content

    def test_command_line_argument_precedence(self):
        """Test that CLI arguments take precedence over environment variables."""
        env_vars = {
            "OPENAI_MODEL": "gpt-4",
            "LITELLM_HOST": "localhost"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([
                "--model", "gpt-5",
                "--host", "127.0.0.1"
            ])

            assert args.model == "gpt-5"  # CLI should override env
            assert args.host == "127.0.0.1"  # CLI should override env

    def test_master_key_configuration(self):
        """Test master key configuration."""
        # Test with master key
        args = parse_args([
            "--master-key", "sk-custom-master",
            "--model", "gpt-5"
        ])

        master_key = None if args.no_master_key else args.master_key
        config_content = render_config(
            alias=args.alias,
            upstream_model=args.model,
            upstream_base=args.upstream_base,
            upstream_key_env=args.upstream_key_env,
            master_key=master_key,
            drop_params=args.drop_params
        )

        assert "sk-custom-master" in config_content
        assert "master_key" in config_content

        # Test without master key
        args = parse_args([
            "--no-master-key",
            "--model", "gpt-5"
        ])

        master_key = None if args.no_master_key else args.master_key
        config_content = render_config(
            alias=args.alias,
            upstream_model=args.model,
            upstream_base=args.upstream_base,
            upstream_key_env=args.upstream_key_env,
            master_key=master_key,
            drop_params=args.drop_params
        )

        assert "master_key" not in config_content

    def test_gpt5_model_variations(self):
        """Test different GPT-5 model configurations."""
        test_cases = [
            {"alias": "gpt5-default", "model": "gpt-5"},
            {"alias": "gpt5-custom", "model": "gpt-5-turbo"},
            {"alias": "gpt5-pro", "model": "gpt-5-pro"}
        ]

        for test_case in test_cases:
            args = parse_args([
                "--alias", test_case["alias"],
                "--model", test_case["model"]
            ])

            master_key = None if args.no_master_key else args.master_key
            config_content = render_config(
                alias=args.alias,
                upstream_model=args.model,
                upstream_base=args.upstream_base,
                upstream_key_env=args.upstream_key_env,
                master_key=master_key,
                drop_params=args.drop_params
            )

            assert test_case["alias"] in config_content
            assert test_case["model"] in config_content

    def test_drop_params_configuration(self):
        """Test drop_params configuration."""
        # Test with drop params (default)
        args = parse_args(["--model", "gpt-5"])

        master_key = None if args.no_master_key else args.master_key
        config_content = render_config(
            alias=args.alias,
            upstream_model=args.model,
            upstream_base=args.upstream_base,
            upstream_key_env=args.upstream_key_env,
            master_key=master_key,
            drop_params=args.drop_params
        )

        assert "drop_params: true" in config_content

        # Test without drop params
        args = parse_args(["--no-drop-params", "--model", "gpt-5"])

        master_key = None if args.no_master_key else args.master_key
        config_content = render_config(
            alias=args.alias,
            upstream_model=args.model,
            upstream_base=args.upstream_base,
            upstream_key_env=args.upstream_key_env,
            master_key=master_key,
            drop_params=args.drop_params
        )

        assert "drop_params: false" in config_content

    def test_upstream_api_configuration(self):
        """Test upstream API configuration."""
        args = parse_args([
            "--model", "gpt-5",
            "--upstream-base", "https://custom-api.example.com/v1",
            "--upstream-key-env", "CUSTOM_API_KEY"
        ])

        master_key = None if args.no_master_key else args.master_key
        config_content = render_config(
            alias=args.alias,
            upstream_model=args.model,
            upstream_base=args.upstream_base,
            upstream_key_env=args.upstream_key_env,
            master_key=master_key,
            drop_params=args.drop_params
        )

        assert "https://custom-api.example.com/v1" in config_content
        assert "os.environ/CUSTOM_API_KEY" in config_content
        assert "gpt-5" in config_content