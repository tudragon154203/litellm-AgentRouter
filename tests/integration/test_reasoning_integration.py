#!/usr/bin/env python3
"""Integration tests for reasoning_effort functionality."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import yaml

from src.config import render_config


class TestReasoningEffortIntegration:
    """Integration tests for reasoning_effort functionality."""

    def test_render_config_with_all_reasoning_levels_integration(self):
        """Test render_config with all reasoning levels using real config generation."""
        reasoning_levels = ["none", "low", "medium", "high"]

        for level in reasoning_levels:
            config_text = render_config(
                alias=f"integration-test-{level}",
                upstream_model="gpt-5",
                upstream_base="https://agentrouter.org/v1",
                upstream_key_env="OPENAI_API_KEY",
                master_key="sk-integration-test",
                drop_params=True,
                streaming=True,
                reasoning_effort=level,
            )

            # Parse the generated YAML to ensure it's valid
            config = yaml.safe_load(config_text)

            # Verify basic structure
            assert "model_list" in config
            assert "litellm_settings" in config

            # Verify model configuration
            model_config = config["model_list"][0]
            assert model_config["model_name"] == f"integration-test-{level}"
            assert model_config["litellm_params"]["model"] == "openai/gpt-5"
            assert model_config["litellm_params"]["api_base"] == "https://agentrouter.org/v1"
            assert model_config["litellm_params"]["api_key"] == "os.environ/OPENAI_API_KEY"

            # Verify reasoning_effort handling
            if level == "none":
                # 'none' should not include reasoning_effort parameter
                assert "reasoning_effort" not in model_config["litellm_params"]
            else:
                # Other levels should include reasoning_effort parameter
                assert model_config["litellm_params"]["reasoning_effort"] == level

    def test_temp_config_creation_with_reasoning(self):
        """Test temporary config creation with reasoning_effort."""
        from src.config import create_temp_config_if_needed

        config_text = render_config(
            alias="temp-reasoning-test",
            upstream_model="gpt-5",
            upstream_base="https://agentrouter.org/v1",
            upstream_key_env="OPENAI_API_KEY",
            master_key=None,
            drop_params=True,
            streaming=True,
            reasoning_effort="medium",
        )

        with create_temp_config_if_needed(config_text, True) as temp_config_path:
            assert temp_config_path.exists()
            assert temp_config_path.suffix == ".yaml"

            # Read and parse the temporary config
            temp_content = temp_config_path.read_text()
            parsed_config = yaml.safe_load(temp_content)

            # Verify reasoning_effort is present in temporary config
            assert parsed_config["model_list"][0]["litellm_params"]["reasoning_effort"] == "medium"

        # File should be deleted after context
        assert not temp_config_path.exists()

    def test_prepare_config_integration_with_reasoning(self):
        """Test prepare_config integration with reasoning_effort."""
        from unittest.mock import MagicMock
        from src.config import prepare_config

        args = MagicMock()
        args.config = None
        args.alias = "prepare-reasoning-test"
        args.model = "gpt-5"
        args.upstream_base = "https://agentrouter.org/v1"
        args.upstream_key_env = "OPENAI_API_KEY"
        args.master_key = "sk-prepare-test"
        args.no_master_key = False
        args.drop_params = True
        args.streaming = True
        args.print_config = False
        args.reasoning_effort = "high"

        config_data, is_generated = prepare_config(args)

        assert is_generated is True
        assert isinstance(config_data, str)

        # Parse and verify the config contains reasoning_effort
        parsed_config = yaml.safe_load(config_data)
        assert parsed_config["model_list"][0]["litellm_params"]["reasoning_effort"] == "high"

    def test_environment_variable_precedence(self):
        """Test that CLI arguments override environment variables."""
        from src.cli import parse_args
        from src.config import prepare_config

        with patch.dict(os.environ, {"REASONING_EFFORT": "low"}):
            # Parse args with CLI override
            args = parse_args([
                "--alias", "precedence-test",
                "--model", "gpt-5",
                "--reasoning-effort", "high"
            ])

            # Prepare config
            config_data, is_generated = prepare_config(args)

            # Verify CLI argument took precedence
            parsed_config = yaml.safe_load(config_data)
            assert parsed_config["model_list"][0]["litellm_params"]["reasoning_effort"] == "high"

    @pytest.mark.slow
    def test_full_config_generation_with_reasoning(self):
        """Test complete configuration generation with reasoning_effort."""
        from src.cli import parse_args
        from src.config import prepare_config

        test_scenarios = [
            {
                "env_reasoning": "low",
                "cli_reasoning": None,
                "expected": "low"
            },
            {
                "env_reasoning": "medium",
                "cli_reasoning": "high",
                "expected": "high"
            },
            {
                "env_reasoning": None,
                "cli_reasoning": "medium",
                "expected": "medium"
            },
            {
                "env_reasoning": None,
                "cli_reasoning": None,
                "expected": "medium"  # Default
            }
        ]

        for scenario in test_scenarios:
            env_patch = {}
            if scenario["env_reasoning"]:
                env_patch["REASONING_EFFORT"] = scenario["env_reasoning"]

            cli_args = [
                "--alias", f"scenario-test-{scenario['expected']}",
                "--model", "gpt-5",
                "--upstream-base", "https://agentrouter.org/v1"
            ]

            if scenario["cli_reasoning"]:
                cli_args.extend(["--reasoning-effort", scenario["cli_reasoning"]])

            with patch.dict(os.environ, env_patch, clear=True):
                args = parse_args(cli_args)
                config_data, is_generated = prepare_config(args)

                parsed_config = yaml.safe_load(config_data)

                if scenario["expected"] == "none":
                    # 'none' should not include reasoning_effort parameter
                    assert "reasoning_effort" not in parsed_config["model_list"][0]["litellm_params"]
                else:
                    assert parsed_config["model_list"][0]["litellm_params"]["reasoning_effort"] == scenario["expected"]

    def test_config_file_parsing_with_reasoning(self):
        """Test that generated config files with reasoning_effort are valid YAML."""
        test_cases = [
            ("none", False),  # Should not include parameter
            ("low", True),
            ("medium", True),
            ("high", True)
        ]

        for reasoning_level, should_include_param in test_cases:
            config_text = render_config(
                alias=f"yaml-test-{reasoning_level}",
                upstream_model="gpt-5",
                upstream_base="https://agentrouter.org/v1",
                upstream_key_env="TEST_KEY",
                master_key="sk-yaml-test",
                drop_params=True,
                streaming=False,
                reasoning_effort=reasoning_level,
            )

            # Ensure it's valid YAML
            parsed_config = yaml.safe_load(config_text)
            assert parsed_config is not None

            # Verify parameter inclusion/exclusion
            has_reasoning = "reasoning_effort" in parsed_config["model_list"][0]["litellm_params"]
            assert has_reasoning == should_include_param

            if should_include_param:
                assert parsed_config["model_list"][0]["litellm_params"]["reasoning_effort"] == reasoning_level

    def test_reasoning_with_existing_config_file(self, tmp_path):
        """Test reasoning_effort when using existing config file."""
        from src.cli import parse_args
        from src.config import prepare_config

        # Create a custom config file
        custom_config = {
            "model_list": [
                {
                    "model_name": "existing-model",
                    "litellm_params": {
                        "model": "openai/gpt-4",
                        "api_base": "https://api.openai.com/v1",
                        "api_key": "os.environ/OPENAI_API_KEY"
                    }
                }
            ],
            "litellm_settings": {
                "drop_params": True
            }
        }

        config_file = tmp_path / "existing_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(custom_config, f)

        # Parse args with existing config and reasoning_effort
        args = parse_args([
            "--config", str(config_file),
            "--reasoning-effort", "high"
        ])

        # Should use existing config file (reasoning_effort should be ignored for existing configs)
        config_data, is_generated = prepare_config(args)
        assert is_generated is False
        assert config_data == config_file

    @pytest.mark.real_api
    def test_end_to_end_reasoning_with_real_api(self, skip_if_no_api_key):
        """End-to-end test with real API call using reasoning_effort (requires API key)."""
        import tempfile
        import subprocess
        import signal
        import time
        import requests

        # Create config with reasoning_effort
        config_text = render_config(
            alias="e2e-reasoning-test",
            upstream_model="gpt-5",
            upstream_base="https://agentrouter.org/v1",
            upstream_key_env="OPENAI_API_KEY",
            master_key="sk-e2e-test",
            drop_params=True,
            streaming=True,
            reasoning_effort="medium",
        )

        # Write config to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_config:
            temp_config.write(config_text)
            temp_config_path = temp_config.name

        try:
            # Start the proxy server
            proc = subprocess.Popen([
                "python", "-m", "src.main",
                "--config", temp_config_path,
                "--host", "127.0.0.1",
                "--port", "0",  # Let system choose port
                "--workers", "1"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Give it time to start
            time.sleep(3)

            # Check if process is still running
            if proc.poll() is None:
                # Process started successfully
                proc.terminate()
                proc.wait(timeout=5)
                success = True
            else:
                # Process failed to start
                stdout, stderr = proc.communicate()
                print(f"Process failed to start. stdout: {stdout.decode()}, stderr: {stderr.decode()}")
                success = False

            assert success, "Proxy server should start successfully with reasoning_effort config"

        finally:
            # Clean up
            if 'proc' in locals() and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
            os.unlink(temp_config_path)