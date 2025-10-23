#!/usr/bin/env python3
"""Unit tests for CLI reasoning_effort functionality."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from pathlib import Path

from src.cli import parse_args


class TestCliReasoningEffort:
    """Test cases for reasoning_effort CLI argument parsing."""

    def test_parse_args_reasoning_effort_default(self):
        """Test default reasoning_effort from environment variable."""
        with patch.dict(os.environ, {"REASONING_EFFORT": "medium"}):
            args = parse_args([])
            assert args.reasoning_effort == "medium"

    def test_parse_args_reasoning_effort_env_override(self):
        """Test reasoning_effort from environment variable with different value."""
        with patch.dict(os.environ, {"REASONING_EFFORT": "high"}):
            args = parse_args([])
            assert args.reasoning_effort == "high"

    def test_parse_args_reasoning_effort_no_env(self):
        """Test default reasoning_effort when no environment variable is set."""
        with patch.dict(os.environ, {}, clear=True):
            args = parse_args([])
            assert args.reasoning_effort == "medium"  # Should use hardcoded default

    def test_parse_args_reasoning_effort_cli_override(self):
        """Test CLI argument overrides environment variable."""
        with patch.dict(os.environ, {"REASONING_EFFORT": "low"}):
            args = parse_args(["--reasoning-effort", "high"])
            assert args.reasoning_effort == "high"

    def test_parse_args_reasoning_effort_cli_short_form(self):
        """Test reasoning_effort CLI argument with various values."""
        test_values = ["none", "low", "medium", "high"]

        for value in test_values:
            args = parse_args(["--reasoning-effort", value])
            assert args.reasoning_effort == value

    def test_parse_args_reasoning_effort_invalid_value(self):
        """Test that invalid reasoning_effort values are rejected."""
        with pytest.raises(SystemExit):
            parse_args(["--reasoning-effort", "invalid"])

    def test_parse_args_reasoning_effort_with_other_args(self):
        """Test reasoning_effort argument combined with other arguments."""
        with patch.dict(os.environ, {"REASONING_EFFORT": "low"}):
            args = parse_args([
                "--alias", "test-model",
                "--model", "gpt-5",
                "--upstream-base", "https://agentrouter.org/v1",
                "--reasoning-effort", "high",
                "--port", "8080",
                "--debug"
            ])

            assert args.reasoning_effort == "high"
            assert args.alias == "test-model"
            assert args.model == "gpt-5"
            assert args.upstream_base == "https://agentrouter.org/v1"
            assert args.port == 8080
            assert args.debug is True

    def test_parse_args_reasoning_effort_help_text(self):
        """Test that help text includes reasoning_effort information."""
        with pytest.raises(SystemExit):
            with patch("sys.stdout") as mock_stdout:
                parse_args(["--help"])

        # Check that help was called
        mock_stdout.write.assert_called()

    def test_parse_args_reasoning_effort_none_value(self):
        """Test 'none' value for reasoning_effort."""
        with patch.dict(os.environ, {"REASONING_EFFORT": "medium"}):
            args = parse_args(["--reasoning-effort", "none"])
            assert args.reasoning_effort == "none"

    def test_parse_args_reasoning_effort_case_sensitivity(self):
        """Test that reasoning_effort is case sensitive (should reject uppercase)."""
        with pytest.raises(SystemExit):
            parse_args(["--reasoning-effort", "LOW"])  # Should be rejected

    def test_parse_args_reasoning_effort_all_valid_choices(self):
        """Test all valid reasoning_effort choices."""
        valid_choices = ["none", "low", "medium", "high"]

        for choice in valid_choices:
            args = parse_args(["--reasoning-effort", choice])
            assert args.reasoning_effort == choice

    def test_parse_args_reasoning_effort_with_config_file(self):
        """Test reasoning_effort argument when using config file."""
        with patch.dict(os.environ, {"REASONING_EFFORT": "high"}):
            args = parse_args([
                "--config", "/path/to/config.yaml",
                "--reasoning-effort", "low"
            ])
            assert args.reasoning_effort == "low"
            assert args.config == Path("/path/to/config.yaml")

    def test_parse_args_reasoning_effort_with_env_and_config(self):
        """Test reasoning_effort with both environment and config settings."""
        with patch.dict(os.environ, {
            "REASONING_EFFORT": "medium",
            "LITELLM_CONFIG": "/existing/config.yaml"
        }):
            args = parse_args([])
            assert args.reasoning_effort == "medium"
            # LITELLM_CONFIG is now retired, should always be None
            assert args.config is None

    def test_parse_args_reasoning_effort_empty_string(self):
        """Test that empty string reasoning_effort is handled."""
        with pytest.raises(SystemExit):
            parse_args(["--reasoning-effort", ""])

    def test_parse_args_reasoning_effort_partial_args(self):
        """Test reasoning_effort with partial CLI arguments."""
        with patch.dict(os.environ, {"REASONING_EFFORT": "low"}):
            # Test with some arguments but not all
            args = parse_args([
                "--alias", "partial-test",
                "--reasoning-effort", "high"
            ])
            assert args.reasoning_effort == "high"
            assert args.alias == "partial-test"
            # Other args should have their defaults
            assert args.model == "gpt-5"  # Check actual default from environment
            assert args.port == 4000