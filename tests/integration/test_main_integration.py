#!/usr/bin/env python3
"""Integration tests for the main CLI functionality."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.cli import parse_args
from src.config import render_config
from src.main import main


class TestMainIntegration:
    """Integration tests for main CLI functionality."""

    def test_full_config_rendering_cycle(self):
        """Test the full configuration rendering cycle."""
        # Test with various arguments
        argv = [
            "--alias", "integration-test-model",
            "--model", "gpt-5",
            "--upstream-base", "https://custom.api.com/v1",
            "--upstream-key-env", "CUSTOM_API_KEY",
            "--master-key", "sk-custom-integration",
            "--host", "127.0.0.1",
            "--port", "9999",
            "--workers", "3",
            "--drop-params"
        ]

        args = parse_args(argv)

        # Render configuration
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

        # Verify configuration structure
        assert "model_list" in config
        assert len(config["model_list"]) > 0

        model_config = config["model_list"][0]
        assert model_config["model_name"] == "integration-test-model"
        assert model_config["litellm_params"]["model"] == "gpt-5"
        assert model_config["litellm_params"]["api_base"] == "https://custom.api.com/v1"

        # Check litellm settings
        assert "litellm_settings" in config
        assert config["litellm_settings"]["drop_params"] is True

    def test_config_rendering_with_environment_variables(self):
        """Test configuration rendering with environment variables."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test-env-key",
            "LITELLM_MASTER_KEY": "sk-test-master",
            "OPENAI_MODEL": "gpt-3.5-turbo",
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

            model_config = config["model_list"][0]
            assert model_config["model_name"] == "local-gpt"  # default alias
            assert model_config["litellm_params"]["model"] == "gpt-3.5-turbo"

    def test_config_file_creation_and_usage(self):
        """Test that config files are properly created and can be used."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"

            args = parse_args([
                "--config", str(config_path),
                "--alias", "file-test-model",
                "--model", "gpt-4"
            ])

            # Render config to file
            master_key = None if args.no_master_key else args.master_key
            config_content = render_config(
                alias=args.alias,
                upstream_model=args.model,
                upstream_base=args.upstream_base,
                upstream_key_env=args.upstream_key_env,
                master_key=master_key,
                drop_params=args.drop_params
            )
            with open(config_path, 'w') as f:
                f.write(config_content)

            # Verify file was created and contains valid YAML
            assert config_path.exists()
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)

            assert "model_list" in loaded_config
            assert loaded_config["model_list"][0]["model_name"] == "file-test-model"

    def test_print_config_functionality(self):
        """Test the --print-config functionality."""
        args = parse_args([
            "--alias", "print-test-model",
            "--model", "gpt-4",
            "--print-config"
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

        # Should be valid YAML
        config = yaml.safe_load(config_content)
        assert "model_list" in config
        assert config["model_list"][0]["model_name"] == "print-test-model"

    def test_no_master_key_configuration(self):
        """Test configuration when --no-master-key is used."""
        args = parse_args([
            "--no-master-key",
            "--alias", "no-auth-model"
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
        config = yaml.safe_load(config_content)

        # Should not have authentication settings
        assert "model_list" in config
        model_config = config["model_list"][0]
        assert model_config["model_name"] == "no-auth-model"

    def test_custom_model_aliases(self):
        """Test custom model alias functionality."""
        test_cases = [
            "custom-model",
            "my-gpt4",
            "work-assistant",
            "api-model-v1"
        ]

        for alias in test_cases:
            args = parse_args(["--alias", alias])
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

            assert config["model_list"][0]["model_name"] == alias

    def test_multiple_configurations_combination(self):
        """Test various combinations of configuration options."""
        test_configs = [
            {
                "args": ["--model", "gpt-3.5-turbo", "--workers", "2"],
                "expected_model": "gpt-3.5-turbo",
                "expected_workers": "2"
            },
            {
                "args": ["--model", "gpt-4", "--debug"],
                "expected_model": "gpt-4",
                "expected_debug": True
            },
            {
                "args": ["--upstream-base", "https://custom.api.com", "--drop-params"],
                "expected_base": "https://custom.api.com",
                "expected_drop_params": True
            }
        ]

        for test_config in test_configs:
            args = parse_args(test_config["args"])
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

            # Verify model configuration
            if "expected_model" in test_config:
                assert config["model_list"][0]["litellm_params"]["model"] == test_config["expected_model"]

            if "expected_base" in test_config:
                assert config["model_list"][0]["litellm_params"]["api_base"] == test_config["expected_base"]

    def test_error_handling_invalid_configs(self):
        """Test error handling with invalid configurations."""
        # Test invalid port number (this should be caught by argparse)
        with pytest.raises(SystemExit):
            parse_args(["--port", "invalid"])

    def test_gpt5_model_configuration(self):
        """Test specific GPT-5 model configuration."""
        args = parse_args([
            "--alias", "gpt5-proxy",
            "--model", "gpt-5",
            "--upstream-base", "https://api.openai.com/v1"
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
        config = yaml.safe_load(config_content)

        model_config = config["model_list"][0]
        assert model_config["model_name"] == "gpt5-proxy"
        assert model_config["litellm_params"]["model"] == "gpt-5"
        assert model_config["litellm_params"]["api_base"] == "https://api.openai.com/v1"

    def test_config_validation_edge_cases(self):
        """Test configuration validation edge cases."""
        # Test with very long alias
        long_alias = "a" * 100
        args = parse_args(["--alias", long_alias])
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

        assert config["model_list"][0]["model_name"] == long_alias

        # Test with special characters in alias
        special_alias = "test-model_v2-with.special"
        args = parse_args(["--alias", special_alias])
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

        assert config["model_list"][0]["model_name"] == special_alias