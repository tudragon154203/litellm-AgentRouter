#!/usr/bin/env python3
"""Integration tests for multi-upstream routing with real proxy."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from textwrap import dedent

import requests


def _find_free_port() -> int:
    """Return an available TCP port on localhost."""
    import socket
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


class TestMultiUpstreamIntegration:
    """Integration tests for multi-upstream configuration with real proxy."""

    def test_proxy_starts_with_multi_upstream_config(self, tmp_path):
        """Test that proxy starts successfully with multi-upstream configuration."""
        # Create config with two upstreams
        config_text = dedent("""
            model_list:
              - model_name: "upstream1-model"
                litellm_params:
                  model: "openai/gpt-3.5-turbo"
                  api_base: "https://upstream1.example.com/v1"
                  api_key: "os.environ/UPSTREAM1_KEY"
                  custom_llm_provider: "openai"
                  mock_response: "Response from upstream1"

              - model_name: "upstream2-model"
                litellm_params:
                  model: "openai/gpt-4"
                  api_base: "https://upstream2.example.com/v1"
                  api_key: "os.environ/UPSTREAM2_KEY"
                  custom_llm_provider: "openai"
                  mock_response: "Response from upstream2"

            general_settings:
              master_key: "sk-test-master"
        """).strip() + "\n"

        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_text, encoding="utf-8")

        port = _find_free_port()
        base_url = f"http://127.0.0.1:{port}"

        env = os.environ.copy()
        env.update({
            "PORT": str(port),
            "LITELLM_HOST": "127.0.0.1",
            "SKIP_PREREQ_CHECK": "1",
            "DISABLE_TELEMETRY": "1",
            "UPSTREAM1_KEY": "sk-test-key-1",
            "UPSTREAM2_KEY": "sk-test-key-2",
        })

        process = subprocess.Popen(
            [sys.executable, "-m", "src.main", "--config", str(config_path)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        try:
            _wait_for_server(base_url, "sk-test-master", timeout=30)

            # Verify models endpoint lists both models
            headers = {"Authorization": "Bearer sk-test-master"}
            response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
            assert response.status_code == 200

            models_data = response.json()
            model_ids = [m["id"] for m in models_data.get("data", [])]
            assert "upstream1-model" in model_ids
            assert "upstream2-model" in model_ids

        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_requests_route_to_correct_upstream(self, tmp_path):
        """Test that requests to different models route to their respective upstreams."""
        config_text = dedent("""
            model_list:
              - model_name: "model-a"
                litellm_params:
                  model: "openai/gpt-3.5-turbo"
                  api_base: "https://upstream-a.example.com/v1"
                  api_key: "os.environ/KEY_A"
                  custom_llm_provider: "openai"
                  mock_response: "Hello from upstream A"

              - model_name: "model-b"
                litellm_params:
                  model: "openai/gpt-4"
                  api_base: "https://upstream-b.example.com/v1"
                  api_key: "os.environ/KEY_B"
                  custom_llm_provider: "openai"
                  mock_response: "Hello from upstream B"

            general_settings:
              master_key: "sk-test-master"
        """).strip() + "\n"

        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_text, encoding="utf-8")

        port = _find_free_port()
        base_url = f"http://127.0.0.1:{port}"

        env = os.environ.copy()
        env.update({
            "PORT": str(port),
            "LITELLM_HOST": "127.0.0.1",
            "SKIP_PREREQ_CHECK": "1",
            "DISABLE_TELEMETRY": "1",
            "KEY_A": "sk-key-a",
            "KEY_B": "sk-key-b",
        })

        process = subprocess.Popen(
            [sys.executable, "-m", "src.main", "--config", str(config_path)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        try:
            _wait_for_server(base_url, "sk-test-master", timeout=30)

            headers = {
                "Authorization": "Bearer sk-test-master",
                "Content-Type": "application/json"
            }

            # Request to model-a
            response_a = requests.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": "model-a",
                    "messages": [{"role": "user", "content": "test"}]
                },
                timeout=10
            )
            assert response_a.status_code == 200
            data_a = response_a.json()
            assert "Hello from upstream A" in data_a["choices"][0]["message"]["content"]

            # Request to model-b
            response_b = requests.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": "model-b",
                    "messages": [{"role": "user", "content": "test"}]
                },
                timeout=10
            )
            assert response_b.status_code == 200
            data_b = response_b.json()
            assert "Hello from upstream B" in data_b["choices"][0]["message"]["content"]

        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
