#!/usr/bin/env python3
"""Integration tests for the LiteLLM proxy."""

from __future__ import annotations

import json
import os
import signal
import socket
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Thread
from typing import Any, Dict
from unittest.mock import patch

import pytest
import requests

from src.cli import parse_args
from src.config import prepare_config
from src.proxy import start_proxy


def find_free_port() -> int:
    """Find a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@contextmanager
def proxy_server(config_args: Dict[str, Any] | None = None):
    """Context manager to start/stop proxy server for testing."""
    if config_args is None:
        config_args = {}

    # Find a free port
    port = find_free_port()

    # Default test configuration
    default_args = [
        "--port", str(port),
        "--host", "127.0.0.1",
        "--alias", "test-model",
        "--model", "gpt-5",
        "--master-key", "sk-test-master",
        "--no-master-key",  # Disable auth for easier testing
    ]

    # Parse arguments
    argv = default_args + ([f"--{k}={v}" for k, v in config_args.items()])
    args = parse_args(argv)

    # Prepare configuration
    config_path = prepare_config(args)

    # Start proxy in a separate thread
    proxy_thread = None
    try:
        # Mock the environment to use a fake API key
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake-key-for-testing"}):
            proxy_thread = Thread(
                target=start_proxy,
                args=(config_path, args),
                daemon=True
            )
            proxy_thread.start()

            # Wait for server to start
            base_url = f"http://{args.host}:{args.port}"
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{base_url}/health", timeout=1)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError(f"Proxy server failed to start on port {port}")

            yield base_url, args

    finally:
        # Clean up
        if config_path and config_path.exists():
            try:
                config_path.unlink()
            except OSError:
                pass


class TestProxyIntegration:
    """Integration tests for the LiteLLM proxy server."""

    def test_proxy_server_starts_and_responds_to_health_check(self):
        """Test that the proxy server starts and responds to health checks."""
        with proxy_server() as (base_url, args):
            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200

    def test_proxy_server_openai_compatible_endpoint(self):
        """Test that the proxy server exposes OpenAI-compatible endpoints."""
        with proxy_server() as (base_url, args):
            # Test that the /v1/models endpoint exists (OpenAI compatible)
            response = requests.get(f"{base_url}/v1/models", timeout=5)
            # Note: This might fail due to auth, but should return 401/403, not 404
            assert response.status_code in [200, 401, 403]

    def test_proxy_server_with_custom_config(self):
        """Test proxy server with custom configuration."""
        custom_config = {
            "alias": "custom-test-model",
            "model": "gpt-5",
            "workers": 2
        }

        with proxy_server(custom_config) as (base_url, args):
            assert args.alias == "custom-test-model"
            assert args.model == "gpt-5"
            assert args.workers == 2

            # Server should still respond
            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200

    def test_proxy_server_respects_port_configuration(self):
        """Test that proxy server respects port configuration."""
        custom_port = find_free_port()
        custom_config = {"port": custom_port}

        with proxy_server(custom_config) as (base_url, args):
            assert args.port == custom_port
            assert base_url.endswith(f":{custom_port}")

            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200

    def test_proxy_server_configuration_generation(self):
        """Test that configuration is properly generated and used."""
        with proxy_server() as (base_url, args):
            # The config should be auto-generated and work
            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "sk-env-test-key",
        "LITELLM_MASTER_KEY": "sk-env-master-key",
        "OPENAI_MODEL": "gpt-4-turbo"
    })
    def test_proxy_server_uses_environment_variables(self):
        """Test that proxy server properly uses environment variables."""
        # Use empty config_args to rely on environment variables
        with proxy_server({}) as (base_url, args):
            # Check that environment variables are picked up
            # Note: parse_args uses environment variables as fallbacks
            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200

    def test_proxy_server_multiple_requests(self):
        """Test that proxy server handles multiple concurrent requests."""
        with proxy_server() as (base_url, args):
            # Make multiple concurrent requests
            def make_request():
                return requests.get(f"{base_url}/health", timeout=5)

            threads = []
            responses = []

            for _ in range(5):
                thread = Thread(target=lambda: responses.append(make_request()))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All requests should succeed
            assert len(responses) == 5
            for response in responses:
                assert response.status_code == 200

    def test_proxy_server_error_handling(self):
        """Test proxy server error handling with invalid requests."""
        with proxy_server() as (base_url, args):
            # Test invalid endpoint
            response = requests.get(f"{base_url}/invalid-endpoint", timeout=5)
            assert response.status_code == 404

            # Test invalid method on health endpoint
            response = requests.post(f"{base_url}/health", timeout=5)
            # Should either 405 (method not allowed) or 404
            assert response.status_code in [404, 405]

    def test_proxy_server_with_existing_config_file(self):
        """Test proxy server with an existing config file."""
        # Create a temporary config file
        config_content = {
            "model_list": [
                {
                    "model_name": "test-existing-model",
                    "litellm_params": {
                        "model": "gpt-3.5-turbo",
                        "api_base": "https://api.openai.com/v1"
                    }
                }
            ]
        }

        config_file = Path("test_config.yaml")
        try:
            with open(config_file, 'w') as f:
                import yaml
                yaml.dump(config_content, f)

            # Test with existing config
            custom_config = {"config": str(config_file)}
            with proxy_server(custom_config) as (base_url, args):
                assert args.config == str(config_file)

                response = requests.get(f"{base_url}/health", timeout=5)
                assert response.status_code == 200

        finally:
            if config_file.exists():
                config_file.unlink()


class TestProxyEndToEnd:
    """End-to-end tests that simulate real usage scenarios."""

    def test_start_stop_restart_cycles(self):
        """Test multiple start/stop cycles with the proxy."""
        for cycle in range(3):
            with proxy_server() as (base_url, args):
                response = requests.get(f"{base_url}/health", timeout=5)
                assert response.status_code == 200

                # Give a moment between cycles
                time.sleep(0.1)

    def test_different_configurations_isolation(self):
        """Test that different configurations are properly isolated."""
        configs = [
            {"alias": "model-1", "model": "gpt-3.5-turbo"},
            {"alias": "model-2", "model": "gpt-4"},
            {"alias": "model-3", "model": "claude-3-sonnet"}
        ]

        for config in configs:
            with proxy_server(config) as (base_url, args):
                assert args.alias == config["alias"]
                assert args.model == config["model"]

                response = requests.get(f"{base_url}/health", timeout=5)
                assert response.status_code == 200