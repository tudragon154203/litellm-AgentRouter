#!/usr/bin/env python3
"""Simplified unit tests for config.py - focusing on core functionality."""

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