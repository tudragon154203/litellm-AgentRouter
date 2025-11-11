#!/usr/bin/env python3
"""
Integration test that exercises the Python proxy routing through the Node helper.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

from src.config.models import ModelSpec
from src.config.rendering import render_config
from tests.integration.conftest import _find_free_port, _wait_for_server


NODE_SCRIPT = Path(__file__).resolve().parents[3] / "node" / "main.mjs"


class MockUpstreamHandler(BaseHTTPRequestHandler):
    """In-memory upstream server that records POST payloads."""

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", 0))
        payload = self.rfile.read(length) if length else b""
        data = json.loads(payload.decode("utf-8")) if payload else {}

        self.server.received.append({
            "path": self.path,
            "headers": {key.lower(): value for key, value in self.headers.items()},
            "body": data,
        })

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if "x-request-id" in self.headers:
            self.send_header("X-Request-ID", self.headers["X-Request-ID"])
        self.end_headers()
        self.wfile.write(json.dumps({
            "choices": [
                {
                    "message": {"content": "node-proxy-ok"}
                }
            ]
        }).encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # pragma: no cover - quiet logging
        return


@pytest.mark.integration
def test_node_upstream_proxy_end_to_end(tmp_path):
    """Spin up Node helper and LiteLLM proxy to validate full stack flow."""
    if shutil.which("node") is None:
        pytest.skip("Node.js runtime not available")

    # Skip if NODE_UPSTREAM_PROXY_ENABLE is set (session fixture is running)
    if os.environ.get("NODE_UPSTREAM_PROXY_ENABLE"):
        pytest.skip("Skipping to avoid conflict with session-scoped Node proxy")

    upstream_port = _find_free_port()
    upstream_server = ThreadingHTTPServer(("127.0.0.1", upstream_port), MockUpstreamHandler)
    upstream_server.received: list[dict[str, object]] = []
    upstream_thread = threading.Thread(target=upstream_server.serve_forever, daemon=True)
    upstream_thread.start()

    node_port = 4000  # Node proxy uses port 4000
    node_env = os.environ.copy()
    node_env.update({
        "OPENAI_BASE_URL": f"http://127.0.0.1:{upstream_port}/v1",
        "OPENAI_API_KEY": "sk-node-upstream",
    })

    try:
        node_process = subprocess.Popen(
            ["node", str(NODE_SCRIPT)],
            env=node_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError) as e:
        pytest.skip(f"Failed to start Node.js process: {e}")

    try:
        # Give Node helper a moment to bind the port
        time.sleep(0.5)

        proxy_port = _find_free_port()
        config_path = tmp_path / "lite-node-config.yaml"
        model_spec = ModelSpec(key="node", alias="node-model", upstream_model="gpt-5")

        config_text = render_config(
            model_specs=[model_spec],
            global_upstream_base=f"http://127.0.0.1:{node_port}/v1",
            master_key="sk-integration-master",
            drop_params=True,
            streaming=True,
            api_key="sk-node-upstream",
        )
        config_path.write_text(config_text, encoding="utf-8")

        python_env = os.environ.copy()
        python_env.update({
            "PORT": str(proxy_port),
            "LITELLM_HOST": "127.0.0.1",
            "SKIP_PREREQ_CHECK": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "LC_ALL": "en_US.UTF-8",
            "LANG": "en_US.UTF-8",
        })

        try:
            python_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "src.main",
                    "--config",
                    str(config_path),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(proxy_port),
                ],
                env=python_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError) as e:
            pytest.skip(f"Failed to start Python proxy process: {e}")

        try:
            _wait_for_server(f"http://127.0.0.1:{proxy_port}", "sk-integration-master", timeout=30.0)

            request_id = "node-integration-test"
            response = requests.post(
                f"http://127.0.0.1:{proxy_port}/v1/chat/completions",
                headers={
                    "Authorization": "Bearer sk-integration-master",
                    "Content-Type": "application/json",
                    "X-Request-ID": request_id,
                },
                json={
                    "model": "node-model",
                    "messages": [{"role": "user", "content": "ping"}],
                    "temperature": 0,
                },
                timeout=15,
            )

            assert response.status_code == 200
            body = response.json()
            assert body["choices"][0]["message"]["content"] == "node-proxy-ok"
            assert upstream_server.received
            upstream_request = upstream_server.received[-1]
            # LiteLLM translates the model alias to the upstream model name
            assert upstream_request["body"].get("model") == "gpt-5"

            # Test request header forwarding
            assert "x-request-id" in upstream_request["headers"]
            assert upstream_request["headers"]["x-request-id"] == request_id

            # Test upstream URL routing
            assert upstream_request["path"] == "/v1/chat/completions"
        finally:
            # Graceful Python proxy cleanup
            try:
                python_process.terminate()
                python_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                python_process.kill()
                python_process.wait()
            except Exception:
                pass  # Best effort cleanup

    finally:
        # Graceful cleanup with timeout handling
        if 'node_process' in locals():
            try:
                node_process.terminate()
                node_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                node_process.kill()
                node_process.wait()
            except Exception:
                pass  # Best effort cleanup

        if 'upstream_server' in locals():
            try:
                upstream_server.shutdown()
            except Exception:
                pass  # Best effort cleanup

        if 'upstream_thread' in locals():
            try:
                upstream_thread.join(timeout=5)
            except Exception:
                pass  # Best effort cleanup


@pytest.mark.integration
def test_node_upstream_proxy_connection_failure(tmp_path):
    """Test handling when upstream Node proxy is unavailable."""
    if shutil.which("node") is None:
        pytest.skip("Node.js runtime not available")

    # Don't start Node process - simulate connection failure
    proxy_port = _find_free_port()
    config_path = tmp_path / "lite-node-fail-config.yaml"
    model_spec = ModelSpec(key="node", alias="node-model", upstream_model="gpt-5")

    config_text = render_config(
        model_specs=[model_spec],
        global_upstream_base="http://127.0.0.1:4000/v1",  # Non-existent Node proxy
        master_key="sk-integration-master",
        drop_params=True,
        streaming=True,
        api_key="sk-node-upstream",
    )
    config_path.write_text(config_text, encoding="utf-8")

    python_env = os.environ.copy()
    python_env.update({
        "PORT": str(proxy_port),
        "LITELLM_HOST": "127.0.0.1",
        "SKIP_PREREQ_CHECK": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "LC_ALL": "en_US.UTF-8",
        "LANG": "en_US.UTF-8",
    })

    python_process = None
    try:
        python_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "src.main",
                "--config",
                str(config_path),
                "--host",
                "127.0.0.1",
                "--port",
                str(proxy_port),
            ],
            env=python_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Give Python proxy time to start
        time.sleep(1.0)

        # Try to make request - should fail gracefully
        try:
            response = requests.post(
                f"http://127.0.0.1:{proxy_port}/v1/chat/completions",
                headers={
                    "Authorization": "Bearer sk-integration-master",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "node-model",
                    "messages": [{"role": "user", "content": "test"}],
                },
                timeout=5,
            )
            # Should either get connection error or 503 from proxy
            assert response.status_code >= 500
        except (requests.ConnectionError, requests.Timeout):
            # Expected when upstream is unavailable
            pass

    finally:
        if python_process:
            try:
                python_process.terminate()
                python_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                python_process.kill()
                python_process.wait()
            except Exception:
                pass
