#!/usr/bin/env python3
"""Pytest configuration for integration tests."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from textwrap import dedent

import pytest
import requests

from src.config.config import runtime_config

_PROXY_MASTER_KEY = "sk-integration-master"
_MOCK_RESPONSE_TEXT = "Hello from LiteLLM integration test"
_INTEGRATION_PROXY_CONFIG = dedent(
    f"""
    model_list:
      - model_name: "mock-gpt"
        litellm_params:
          model: "gpt-3.5-turbo"
          mock_response: "{_MOCK_RESPONSE_TEXT}"
          temperature: 0

    general_settings:
      master_key: "{_PROXY_MASTER_KEY}"
    """
).strip() + "\n"


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
    runtime_config.ensure_loaded()


@pytest.fixture
def skip_if_no_api_key():
    """Skip test if no API key is available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")


def _find_free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_server(base_url: str, master_key: str, timeout: float = 30.0) -> None:
    """Poll the proxy until the models endpoint responds successfully."""
    deadline = time.time() + timeout
    headers = {"Authorization": f"Bearer {master_key}"}

    while time.time() < deadline:
        try:
            response = requests.get(
                f"{base_url}/v1/models", headers=headers, timeout=1
            )
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)

    raise RuntimeError(
        f"LiteLLM proxy did not become ready at {base_url}/v1/models within {timeout}s"
    )


@pytest.fixture(scope="session")
def proxy_server(tmp_path_factory: pytest.TempPathFactory):
    """Start a real LiteLLM proxy backed by mock responses for integration tests."""
    config_dir = tmp_path_factory.mktemp("proxy-config")
    config_path = config_dir / "litellm-config.yaml"
    config_path.write_text(_INTEGRATION_PROXY_CONFIG, encoding="utf-8")

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env.update(
        {
            "PORT": str(port),
            "LITELLM_HOST": "127.0.0.1",
            "SKIP_PREREQ_CHECK": "1",
            "DISABLE_TELEMETRY": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "LC_ALL": "en_US.UTF-8",
            "LANG": "en_US.UTF-8",
        }
    )

    process = subprocess.Popen(
        [sys.executable, "-m", "src.main", "--config", str(config_path)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_for_server(base_url, _PROXY_MASTER_KEY)
        yield {
            "base_url": base_url,
            "headers": {"Authorization": f"Bearer {_PROXY_MASTER_KEY}"},
            "model": "mock-gpt",
            "upstream_model": "gpt-3.5-turbo",
            "mock_response": _MOCK_RESPONSE_TEXT,
            "master_key": _PROXY_MASTER_KEY,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
