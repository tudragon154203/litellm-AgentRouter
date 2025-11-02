#!/usr/bin/env python3
"""
Additional tests to improve coverage of config module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config.models import ModelSpec
from src.config.parsing import load_model_specs_from_env, prepare_config
from src.config.rendering import render_config


class TestModelSpecCoverage:
    """Test edge cases for ModelSpec validation."""

    def test_model_spec_empty_key(self):
        """Test ModelSpec validation with empty key."""
        with pytest.raises(ValueError, match="Model key cannot be empty"):
            ModelSpec(
                key="",
                alias="test-model",
                upstream_model="gpt-5"
            )

    def test_model_spec_empty_alias(self):
        """Test ModelSpec validation with empty alias - should be auto-derived from upstream."""
        spec = ModelSpec(
            key="test",
            alias="",  # Will be auto-derived
            upstream_model="gpt-5"
        )
        assert spec.alias == "gpt-5"  # Auto-derived from upstream

    def test_model_spec_none_alias(self):
        """Alias of None should also be auto-derived."""
        spec = ModelSpec(
            key="test",
            alias=None,  # type: ignore[arg-type]
            upstream_model="openai/gpt-5",
        )
        assert spec.alias == "gpt-5"

    def test_model_spec_empty_upstream_model(self):
        """Test ModelSpec validation with empty upstream model."""
        with pytest.raises(ValueError, match="Upstream model cannot be empty"):
            ModelSpec(
                key="test",
                alias="test-model",
                upstream_model=""
            )


class TestLoadModelSpecsFromEnvCoverage:
    """Test edge cases for load_model_specs_from_env."""

    def test_legacy_alias_env_var_raises(self):
        """Legacy MODEL_XXX_ALIAS variables should raise a helpful error."""
        with patch.dict(os.environ, {
            "PROXY_MODEL_KEYS": "test",
            "MODEL_TEST_ALIAS": "legacy-alias",
            "MODEL_TEST_UPSTREAM_MODEL": "gpt-5",
        }, clear=True):
            with pytest.raises(
                ValueError,
                match="Legacy environment variable 'MODEL_TEST_ALIAS' detected",
            ):
                load_model_specs_from_env()

    def test_missing_upstream_model_env_var(self):
        """Test error when MODEL_XXX_UPSTREAM_MODEL is missing."""
        with patch.dict(os.environ, {
            "PROXY_MODEL_KEYS": "test",
        }, clear=True):
            with pytest.raises(ValueError, match="Missing environment variable: MODEL_TEST_UPSTREAM_MODEL"):
                load_model_specs_from_env()


class TestRenderConfigCoverage:
    """Test edge cases for render_config."""

    def test_render_config_with_no_api_key(self):
        """Test rendering config when no upstream key env is specified."""
        model_spec = ModelSpec(
            key="test",
            alias="test-model",
            upstream_model="gpt-5",
            upstream_key_env=None
        )

        config_text = render_config(
            model_specs=[model_spec],
            global_upstream_base="https://api.openai.com",
            global_upstream_key_env=None,
            master_key="sk-test",
            drop_params=True,
            streaming=True
        )

        assert "api_key: null" in config_text

    def test_render_config_with_reasoning_unsupported_model(self):
        """Test rendering config with reasoning effort for unsupported model."""
        # Mock a model that explicitly doesn't support reasoning
        with patch('src.config.get_model_capabilities') as mock_caps:
            mock_caps.return_value = {"supports_reasoning": False}

            model_spec = ModelSpec(
                key="test",
                alias="test-model",
                upstream_model="unsupported-model",
                reasoning_effort="high"
            )

            with patch('builtins.print') as mock_print:
                render_config(
                    model_specs=[model_spec],
                    global_upstream_base="https://api.openai.com",
                    global_upstream_key_env="API_KEY",
                    master_key="sk-test",
                    drop_params=True,
                    streaming=True
                )

                # Should print warning
                mock_print.assert_called()
                warning_call = str(mock_print.call_args[0][0])
                assert "WARNING: Model unsupported-model does not support reasoning_effort" in warning_call
                assert "ignoring reasoning_effort=high" in warning_call


class TestPrepareConfigCoverage:
    """Test edge cases for prepare_config."""

    def test_prepare_config_missing_config_file(self):
        """Test error when config file doesn't exist."""
        from unittest.mock import MagicMock
        mock_args = MagicMock()
        mock_args.config = "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found: nonexistent.yaml"):
            prepare_config(mock_args)

    def test_prepare_config_with_missing_env_vars(self):
        """Test prepare_config with model specs having missing env vars."""
        from unittest.mock import MagicMock
        mock_args = MagicMock()
        mock_args.config = None
        mock_args.model_specs = [
            ModelSpec(
                key="test",
                alias="test-model",
                upstream_model="gpt-5",
                upstream_key_env="MISSING_API_KEY"
            )
        ]
        mock_args.no_master_key = False
        mock_args.master_key = "sk-local-master"
        mock_args.upstream_base = None
        mock_args.upstream_key_env = None
        mock_args.drop_params = True
        mock_args.streaming = True
        mock_args.print_config = False

        with patch('builtins.print') as mock_print:
            with patch.dict(os.environ, {}, clear=True):
                config_text, is_generated = prepare_config(mock_args)

                # Should print warning about missing env var
                mock_print.assert_called()
                warning_call = str(mock_print.call_args[0][0])
                assert "WARNING: Environment variable 'MISSING_API_KEY'" in warning_call
                assert "for model 'test-model' is not set" in warning_call


class TestCreateTempConfigCoverage:
    """Test edge cases for create_temp_config_if_needed."""

    def test_create_temp_config_with_existing_path(self):
        """Test when config_data is an existing path (not generated)."""
        from src.config import create_temp_config_if_needed
        from unittest.mock import patch

        # Create a temporary file
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_file.__exit__.return_value = None
            mock_open.return_value = mock_file

            existing_path = Path("/tmp/test_config.yaml")

            with create_temp_config_if_needed(existing_path, False) as config_path:
                assert config_path == existing_path
                # Should not open file for writing since it's existing
                mock_open.assert_not_called()
