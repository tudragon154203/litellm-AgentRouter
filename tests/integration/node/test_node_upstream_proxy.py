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


NODE_SCRIPT = Path(__file__).resolve().parents[3] / "node" / "upstream-proxy.mjs"


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

    upstream_port = _find_free_port()
    upstream_server = ThreadingHTTPServer(("127.0.0.1", upstream_port), MockUpstreamHandler)
    upstream_server.received: list[dict[str, object]] = []
    upstream_thread = threading.Thread(target=upstream_server.serve_forever, daemon=True)
    upstream_thread.start()

    node_port = _find_free_port()
    node_env = os.environ.copy()
    node_env.update({
        "NODE_UPSTREAM_PROXY_PORT": str(node_port),
        "OPENAI_BASE_URL": f"http://127.0.0.1:{upstream_port}/v1",
        "OPENAI_API_KEY": "sk-node-upstream",
    })

    node_process = subprocess.Popen(
        ["node", str(NODE_SCRIPT)],
        env=node_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

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
        finally:
            python_process.terminate()
            python_process.wait(timeout=10)

    finally:
        node_process.terminate()
        node_process.wait(timeout=10)
        upstream_server.shutdown()
        upstream_thread.join(timeout=5)
