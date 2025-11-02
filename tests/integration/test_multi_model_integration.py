#!/usr/bin/env python3
"""Integration tests for multi-model configuration."""

from __future__ import annotations

import os
import subprocess


class TestMultiModelIntegration:
    """Integration tests for multi-model configurations."""

    def test_print_config_dual_model_env(self):
        """Test --print-config with dual-model environment configuration."""
        env_vars = {
            "PROXY_MODEL_KEYS": "gpt5,deepseek",
            "MODEL_GPT5_ALIAS": "gpt-5",
            "MODEL_GPT5_UPSTREAM_MODEL": "gpt-5",
            "MODEL_GPT5_REASONING_EFFORT": "medium",
            "MODEL_DEEPSEEK_ALIAS": "deepseek-v3.2",
            "MODEL_DEEPSEEK_UPSTREAM_MODEL": "deepseek-v3.2",
            "MODEL_DEEPSEEK_REASONING_EFFORT": "low",
            "OPENAI_API_BASE": "https://agentrouter.org/v1",
            "OPENAI_API_KEY": "sk-test-key",
            "LITELLM_MASTER_KEY": "sk-master-test",
            "SKIP_PREREQ_CHECK": "1",
        }

        result = subprocess.run(
            [
                "python", "-m", "src.main",
                "--print-config"
            ],
            capture_output=True,
            text=True,
            env={**os.environ, **env_vars},
        )

        assert result.returncode == 0
        config_text = result.stdout

        # Check that both models are present
        assert 'model_name: "gpt-5"' in config_text
        assert 'model_name: "deepseek-v3.2"' in config_text

        # Check upstream models
        assert 'model: "openai/gpt-5"' in config_text
        assert 'model: "openai/deepseek-v3.2"' in config_text

        # Check reasoning effort entries
        assert 'reasoning_effort: "medium"' in config_text
        assert 'reasoning_effort: "low"' in config_text

        # Check global settings
        assert "drop_params: true" in config_text
        assert "set_verbose: true" in config_text
        assert 'master_key: "sk-master-test"' in config_text

    def test_print_config_single_model_env(self):
        """Test --print-config with single model environment configuration."""
        env_vars = {
            "PROXY_MODEL_KEYS": "primary",
            "MODEL_PRIMARY_ALIAS": "primary-model",
            "MODEL_PRIMARY_UPSTREAM_MODEL": "gpt-5",
            "MODEL_PRIMARY_REASONING_EFFORT": "high",
            "OPENAI_API_BASE": "https://custom.api.com",
            "OPENAI_API_KEY": "sk-custom-key",
            "SKIP_PREREQ_CHECK": "1",
        }

        result = subprocess.run(
            [
                "python", "-m", "src.main",
                "--print-config"
            ],
            capture_output=True,
            text=True,
            env={**os.environ, **env_vars},
        )

        assert result.returncode == 0
        config_text = result.stdout

        assert 'model_name: "primary-model"' in config_text
        assert 'model: "openai/gpt-5"' in config_text
        assert 'reasoning_effort: "high"' in config_text
        assert 'api_base: "https://custom.api.com"' in config_text

    def test_print_config_cli_multi_model(self):
        """Test --print-config with CLI multi-model specifications."""
        result = subprocess.run(
            [
                "python", "-m", "src.main",
                "--model-spec", "key=gpt5,alias=gpt-5,upstream=gpt-5,reasoning=medium",
                "--model-spec", "key=deepseek,alias=deepseek-v3.2,upstream=deepseek-v3.2,reasoning=none",
                "--upstream-base", "https://cli.api.com",
                "--master-key", "sk-cli-master",
                "--print-config"
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "SKIP_PREREQ_CHECK": "1"}
        )

        assert result.returncode == 0
        config_text = result.stdout

        # Check both models from CLI
        assert 'model_name: "gpt-5"' in config_text
        assert 'model_name: "deepseek-v3.2"' in config_text

        # Check CLI-specified base URL is used
        assert 'api_base: "https://cli.api.com"' in config_text
        assert config_text.count('api_base: "https://cli.api.com"') == 2  # Both models should use it

        # Check reasoning effort handling
        assert 'reasoning_effort: "medium"' in config_text
        # DeepSeek should NOT have reasoning effort
        lines = config_text.split('\n')
        deepseek_section = False
        for i, line in enumerate(lines):
            if 'model_name: "deepseek-v3.2"' in line:
                deepseek_section = True
            if deepseek_section and "reasoning_effort:" in line:
                # Check if next section starts before finding reasoning
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith('- model_name:') or 'litellm_settings:' in lines[j]:
                        assert False, "DeepSeek should not have reasoning_effort"

    def test_startup_message_dual_model(self):
        """Test startup message displays all configured models."""
        env_vars = {
            "PROXY_MODEL_KEYS": "gpt5,deepseek",
            "MODEL_GPT5_ALIAS": "gpt-5",
            "MODEL_GPT5_UPSTREAM_MODEL": "gpt-5",
            "MODEL_DEEPSEEK_ALIAS": "deepseek-v3.2",
            "MODEL_DEEPSEEK_UPSTREAM_MODEL": "deepseek-v3.2",
        }

        result = subprocess.run(
            [
                "python", "-c",
                """
import sys
sys.path.insert(0, 'src')
from src.main import get_startup_message
from src.cli import parse_args
from src.config import prepare_config

args = parse_args([])
prepare_config(args)
print(get_startup_message(args))
"""
            ],
            capture_output=True,
            text=True,
            env={**os.environ, **env_vars}
        )

        assert result.returncode == 0
        startup_msg = result.stdout.strip()

        assert "with 2 model(s):" in startup_msg
        assert "gpt-5 (gpt-5)" in startup_msg
        assert "deepseek-v3.2 (deepseek-v3.2)" in startup_msg

    def test_startup_message_single_model(self):
        """Test startup message for single model."""
        env_vars = {
            "PROXY_MODEL_KEYS": "primary",
            "MODEL_PRIMARY_ALIAS": "primary-model",
            "MODEL_PRIMARY_UPSTREAM_MODEL": "gpt-5",
        }

        result = subprocess.run(
            [
                "python", "-c",
                """
import sys
sys.path.insert(0, 'src')
from src.main import get_startup_message
from src.cli import parse_args
from src.config import prepare_config

args = parse_args([])
prepare_config(args)
print(get_startup_message(args))
"""
            ],
            capture_output=True,
            text=True,
            env={**os.environ, **env_vars}
        )

        assert result.returncode == 0
        startup_msg = result.stdout.strip()

        assert "with 1 model(s):" in startup_msg
        assert "primary-model (gpt-5)" in startup_msg

    def test_legacy_single_model_requires_new_schema(self):
        """Legacy single-model flags without model specs should fail."""
        # Create a clean environment without any PROXY_MODEL_KEYS or model variables
        clean_env = {}
        # Keep only essential environment variables
        for key in ["PATH", "PYTHONPATH", "SYSTEMROOT", "COMSPEC", "PATHEXT"]:
            if key in os.environ:
                clean_env[key] = os.environ[key]

        clean_env["SKIP_PREREQ_CHECK"] = "1"
        clean_env["SKIP_DOTENV"] = "1"

        result = subprocess.run(
            [
                "python", "-m", "src.main",
                "--alias", "legacy-model",
                "--model", "gpt-5",
                "--reasoning-effort", "low",
                "--print-config"
            ],
            capture_output=True,
            text=True,
            env=clean_env
        )

        assert result.returncode != 0
        assert "PROXY_MODEL_KEYS" in result.stderr or "model specifications" in result.stderr

    def test_error_handling_missing_env_vars(self):
        """Test error handling for missing required environment variables."""
        # Create a clean environment and only set the test-specific variables
        clean_env = {}
        # Keep only essential environment variables
        for key in ["PATH", "PYTHONPATH", "SYSTEMROOT", "COMSPEC", "PATHEXT"]:
            if key in os.environ:
                clean_env[key] = os.environ[key]

        # Add test-specific environment variables
        env_vars = {
            "PROXY_MODEL_KEYS": "gpt5",
            "MODEL_GPT5_ALIAS": "gpt-5",
            # Missing MODEL_GPT5_UPSTREAM_MODEL intentionally
            "SKIP_PREREQ_CHECK": "1",
            "SKIP_DOTENV": "1"
        }
        clean_env.update(env_vars)

        result = subprocess.run(
            [
                "python", "-m", "src.main",
                "--print-config"
            ],
            capture_output=True,
            text=True,
            env=clean_env
        )

        assert result.returncode != 0
        assert "ERROR" in result.stderr
        assert "MODEL_GPT5_UPSTREAM_MODEL" in result.stderr

    def test_config_yaml_ordering(self):
        """Test that generated YAML has correct ordering for snapshot testing."""
        env_vars = {
            "PROXY_MODEL_KEYS": "gpt5,deepseek",
            "MODEL_GPT5_ALIAS": "gpt-5",
            "MODEL_GPT5_UPSTREAM_MODEL": "gpt-5",
            "MODEL_DEEPSEEK_ALIAS": "deepseek-v3.2",
            "MODEL_DEEPSEEK_UPSTREAM_MODEL": "deepseek-v3.2",
            "OPENAI_API_BASE": "https://agentrouter.org/v1",
            "OPENAI_API_KEY": "sk-test",
        }

        result = subprocess.run(
            [
                "python", "-m", "src.main",
                "--print-config"
            ],
            capture_output=True,
            text=True,
            env={**os.environ, **env_vars, "SKIP_PREREQ_CHECK": "1"}
        )

        assert result.returncode == 0
        config_lines = result.stdout.strip().split('\n')

        # Verify basic structure order
        assert config_lines[0] == "model_list:"

        # Find model sections and verify order
        gpt5_line_idx = next(i for i, line in enumerate(config_lines) if 'model_name: "gpt-5"' in line)
        deepseek_line_idx = next(i for i, line in enumerate(config_lines) if 'model_name: "deepseek-v3.2"' in line)

        # GPT-5 should come first (matching PROXY_MODEL_KEYS order)
        assert gpt5_line_idx < deepseek_line_idx

        # Verify litellm_settings comes after all models
        litellm_settings_idx = next(i for i, line in enumerate(config_lines) if "litellm_settings:" in line)
        assert litellm_settings_idx > gpt5_line_idx
        assert litellm_settings_idx > deepseek_line_idx
