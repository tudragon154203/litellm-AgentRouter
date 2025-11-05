#!/usr/bin/env python3
"""Shared test fixtures for LiteLLM tests."""

from __future__ import annotations

import pytest

from src.config.config import runtime_config


@pytest.fixture
def config_overrides():
    """Fixture for temporarily overriding configuration values in tests.

    Usage:
        def test_something(config_overrides):
            with config_overrides({"KEY": "value"}):
                # Test code that sees the overridden value
                pass
    """
    def _override(overrides: dict[str, str]):
        return runtime_config.override(overrides)

    return _override
