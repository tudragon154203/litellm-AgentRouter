#!/usr/bin/env python3
"""Integration tests for backward compatibility with legacy single-upstream config."""

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


class TestBackwardCompatibility:
    """Integration tests for backward compatibility with legacy configurations."""

    def test_proxy_starts_with_legacy_single_upstream_config(self, tmp_path, monkeypatch):
        """Test proxy startup with legacy single-upstream environment config."""
        # Set legacy environment variables (no MODEL_<KEY>_UPSTREAM)
        monkeypatch.setenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("PROXY_MODEL_KEYS", "gpt5,deepseek")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("MODEL_DEEPSEEK_UPSTREAM_MODEL", "deepseek-v3.2")
        monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-test-master")

        port = _find_free_port()
        base_url = f"http://127.0.0.1:{port}"

        env = os.environ.copy()
        env.update({
            "PORT": str(port),
            "LITELLM_HOST": "127.0.0.1",
            "SKIP_PREREQ_CHECK": "1",
            "DISABLE_TELEMETRY": "1",
        })

        process = subprocess.Popen(
            [sys.executable, "-m", "src.main"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        try:
            _wait_for_server(base_url, "sk-test-master", timeout=30)

            # Verify models endpoint works
            headers = {"Authorization": "Bearer sk-test-master"}
            response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
            assert response.status_code == 200

            models_data = response.json()
            model_ids = [m["id"] for m in models_data.get("data", [])]
            assert "gpt-5" in model_ids
            assert "deepseek-v3.2" in model_ids

        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_models_use_global_openai_base_url_and_api_key(self, tmp_path):
        """Verify models without MODEL_<KEY>_UPSTREAM use global OPENAI_BASE_URL and OPENAI_API_KEY."""
        # Create config that would be generated from legacy env vars
        config_text = dedent("""
            model_list:
              - model_name: "gpt-5"
                litellm_params:
                  model: "openai/gpt-5"
                  api_base: "https://agentrouter.org/v1"
                  api_key: "os.environ/OPENAI_API_KEY"
                  custom_llm_provider: "openai"
                  mock_response: "Legacy config response"

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
            "OPENAI_API_KEY": "sk-legacy-key",
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

            # Make a request to verify it works
            response = requests.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": "gpt-5",
                    "messages": [{"role": "user", "content": "test"}]
                },
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            assert "Legacy config response" in data["choices"][0]["message"]["content"]

        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_no_migration_required_for_existing_configs(self, tmp_path, monkeypatch):
        """Test that existing configurations work without any migration."""
        # Simulate an existing .env file with no multi-upstream variables
        monkeypatch.setenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-existing-key")
        monkeypatch.setenv("PROXY_MODEL_KEYS", "gpt5")
        monkeypatch.setenv("MODEL_GPT5_UPSTREAM_MODEL", "gpt-5")
        monkeypatch.setenv("MODEL_GPT5_REASONING_EFFORT", "medium")
        monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-test-master")

        port = _find_free_port()
        base_url = f"http://127.0.0.1:{port}"

        env = os.environ.copy()
        env.update({
            "PORT": str(port),
            "LITELLM_HOST": "127.0.0.1",
            "SKIP_PREREQ_CHECK": "1",
            "DISABLE_TELEMETRY": "1",
        })

        process = subprocess.Popen(
            [sys.executable, "-m", "src.main"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        try:
            _wait_for_server(base_url, "sk-test-master", timeout=30)

            # Verify proxy started and model is available
            headers = {"Authorization": "Bearer sk-test-master"}
            response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
            assert response.status_code == 200

            models_data = response.json()
            model_ids = [m["id"] for m in models_data.get("data", [])]
            assert "gpt-5" in model_ids

        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
