#!/usr/bin/env python3
"""Unit tests for model spec validation."""

from __future__ import annotations

import pytest

from src.config.models import ModelSpec
from src.config.parsing import validate_model_specs


class TestValidateModelSpecs:
    """Tests for model specification validation."""

    def test_validation_passes_with_unique_upstream_models(self):
        """Validation should pass when all upstream model names are unique."""
        specs = [
            ModelSpec(key="gpt5", alias="gpt-5", upstream_model="gpt-5"),
            ModelSpec(key="deepseek", alias="deepseek-v3.2", upstream_model="deepseek-v3.2"),
            ModelSpec(key="claude", alias="claude-4.5-sonnet", upstream_model="claude-4.5-sonnet"),
        ]

        # Should not raise
        validate_model_specs(specs)

    def test_detect_duplicate_upstream_model_names(self):
        """Validation should detect duplicate upstream model names."""
        specs = [
            ModelSpec(key="gpt5_agentrouter", alias="gpt-5-ar", upstream_model="gpt-5"),
            ModelSpec(key="gpt5_hubs", alias="gpt-5-hubs", upstream_model="gpt-5"),
        ]

        with pytest.raises(ValueError, match="Duplicate upstream model name"):
            validate_model_specs(specs)

    def test_error_message_lists_conflicting_models(self):
        """Error message should list all conflicting model keys."""
        specs = [
            ModelSpec(key="model1", alias="alias1", upstream_model="gpt-5"),
            ModelSpec(key="model2", alias="alias2", upstream_model="gpt-5"),
            ModelSpec(key="model3", alias="alias3", upstream_model="gpt-5"),
        ]

        with pytest.raises(ValueError) as exc_info:
            validate_model_specs(specs)

        error_msg = str(exc_info.value)
        assert "gpt-5" in error_msg
        assert "model1" in error_msg
        assert "model2" in error_msg
        assert "model3" in error_msg

    def test_multiple_duplicate_groups(self):
        """Validation should detect multiple groups of duplicates."""
        specs = [
            ModelSpec(key="gpt5_1", alias="gpt-5-1", upstream_model="gpt-5"),
            ModelSpec(key="gpt5_2", alias="gpt-5-2", upstream_model="gpt-5"),
            ModelSpec(key="claude_1", alias="claude-1", upstream_model="claude-4.5-sonnet"),
            ModelSpec(key="claude_2", alias="claude-2", upstream_model="claude-4.5-sonnet"),
        ]

        with pytest.raises(ValueError) as exc_info:
            validate_model_specs(specs)

        error_msg = str(exc_info.value)
        assert "gpt-5" in error_msg
        assert "claude-4.5-sonnet" in error_msg

    def test_validation_with_empty_list(self):
        """Validation should pass with empty model list."""
        validate_model_specs([])

    def test_validation_with_single_model(self):
        """Validation should pass with single model."""
        specs = [ModelSpec(key="gpt5", alias="gpt-5", upstream_model="gpt-5")]
        validate_model_specs(specs)
