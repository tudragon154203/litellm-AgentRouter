#!/usr/bin/env python3
"""Pytest configuration for integration tests."""

from __future__ import annotations

import os
import pytest
from src.utils import load_dotenv_files


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "real_api: marks tests as requiring real API calls"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test content."""
    for item in items:
        # Add real_api marker to tests that make actual API calls
        if "real_gpt5_api" in str(item.fspath) and "test_" in item.name:
            item.add_marker(pytest.mark.real_api)
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session", autouse=True)
def load_test_environment():
    """Load environment variables for all tests."""
    load_dotenv_files()


@pytest.fixture
def skip_if_no_api_key():
    """Skip test if no API key is available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")


