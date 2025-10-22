#!/usr/bin/env python3
"""Integration tests specifically for GPT-5 model functionality."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import yaml

from src.cli import parse_args
from src.config import render_config


class TestGPT5Integration:
    """Integration tests specifically for GPT-5 model configuration."""

    def test_gpt5_model_configuration(self):
        """Test specific GPT-5 model configuration."""
        args = parse_args([
            "--alias", "gpt5-proxy",
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
        config = yaml.safe_load(config_content)

        model_config = config["model_list"][0]
        assert model_config["model_name"] == "gpt5-proxy"
        assert model_config["litellm_params"]["model"] == "gpt-5"
        assert model_config["litellm_params"]["api_base"] == "https://api.openai.com/v1"
        assert model_config["litellm_params"]["api_key"] == "os.environ/OPENAI_API_KEY"

    def test_gpt5_model_variations(self):
        """Test different GPT-5 model configurations."""
        test_cases = [
            {"alias": "gpt5-default", "model": "gpt-5"},
            {"alias": "gpt5-turbo", "model": "gpt-5-turbo"},
            {"alias": "gpt5-pro", "model": "gpt-5-pro"},
            {"alias": "gpt5-vision", "model": "gpt-5-vision-preview"}
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
            config = yaml.safe_load(config_content)

            assert config["model_list"][0]["model_name"] == test_case["alias"]
            assert config["model_list"][0]["litellm_params"]["model"] == test_case["model"]

    def test_gpt5_with_different_upstreams(self):
        """Test GPT-5 with different upstream providers."""
        upstreams = [
            {"base": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY"},
            {"base": "https://api.anthropic.com/v1", "key_env": "ANTHROPIC_API_KEY"},
            {"base": "https://api.custom-llm.com/v1", "key_env": "CUSTOM_LLM_KEY"}
        ]

        for upstream in upstreams:
            args = parse_args([
                "--alias", "gpt5-custom",
                "--model", "gpt-5",
                "--upstream-base", upstream["base"],
                "--upstream-key-env", upstream["key_env"]
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
            assert model_config["litellm_params"]["model"] == "gpt-5"
            assert model_config["litellm_params"]["api_base"] == upstream["base"]
            assert model_config["litellm_params"]["api_key"] == f"os.environ/{upstream['key_env']}"

    def test_gpt5_with_authentication_variations(self):
        """Test GPT-5 with different authentication configurations."""
        # Test with master key
        args = parse_args([
            "--model", "gpt-5",
            "--master-key", "sk-gpt5-master"
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

        assert "sk-gpt5-master" in config_content
        assert "master_key" in config_content
        assert "gpt-5" in config_content

        # Test without master key
        args = parse_args([
            "--model", "gpt-5",
            "--no-master-key"
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
        assert "gpt-5" in config_content

    def test_gpt5_environment_variable_integration(self):
        """Test GPT-5 configuration with environment variables."""
        env_vars = {
            "OPENAI_API_KEY": "sk-gpt5-env-key",
            "OPENAI_MODEL": "gpt-5",
            "OPENAI_BASE_URL": "https://api.openai.com/v1"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            args = parse_args([])  # Should use GPT-5 from environment

            assert args.model == "gpt-5"

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
            assert "os.environ/OPENAI_API_KEY" in config_content

    def test_gpt5_drop_params_configuration(self):
        """Test GPT-5 with drop_params configuration."""
        # Test with drop params enabled (default)
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
        assert "gpt-5" in config_content

        # Test with drop params disabled
        args = parse_args(["--model", "gpt-5", "--no-drop-params"])

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
        assert "gpt-5" in config_content

    def test_gpt5_with_custom_ports_and_hosts(self):
        """Test GPT-5 configuration with custom ports and hosts."""
        network_configs = [
            {"host": "localhost", "port": 8080},
            {"host": "127.0.0.1", "port": 9000},
            {"host": "0.0.0.0", "port": 4000}
        ]

        for net_config in network_configs:
            args = parse_args([
                "--model", "gpt-5",
                "--host", net_config["host"],
                "--port", str(net_config["port"])
            ])

            assert args.model == "gpt-5"
            assert args.host == net_config["host"]
            assert args.port == net_config["port"]

            # Verify config generation
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

    def test_gpt5_multiple_alias_configurations(self):
        """Test multiple GPT-5 configurations with different aliases."""
        alias_configs = [
            "primary-gpt5",
            "gpt5-work",
            "gpt5-personal",
            "gpt5-experimental"
        ]

        for alias in alias_configs:
            args = parse_args([
                "--alias", alias,
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
            config = yaml.safe_load(config_content)

            assert config["model_list"][0]["model_name"] == alias
            assert config["model_list"][0]["litellm_params"]["model"] == "gpt-5"