#!/usr/bin/env python3
"""Tests for the Node proxy subprocess helper."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.node.process import NodeProxyProcess


def _create_node_script(tmp_path: Path) -> Path:
    script = tmp_path / "upstream-proxy.mjs"
    script.write_text("// dummy node proxy")
    return script


def test_build_env_applies_runtime_settings(monkeypatch, tmp_path):
    script = _create_node_script(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-node")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://custom.upstream/v1")
    monkeypatch.setenv("SKIP_DOTENV", "1")

    monkeypatch.setattr("src.node.process.build_user_agent", lambda: "QwenCode/test-agent")
    node_process = NodeProxyProcess(node_script=script)
    env = node_process._build_env()

    assert env["OPENAI_BASE_URL"] == "https://custom.upstream/v1"
    assert env["NODE_USER_AGENT"] == "QwenCode/test-agent"
    assert env["OPENAI_API_KEY"] == "sk-node"


def test_start_requires_api_key(tmp_path):
    script = _create_node_script(tmp_path)
    env = {
        "PATH": os.getenv("PATH", ""),
        "SKIP_DOTENV": "1",
    }
    with patch.dict(os.environ, env, clear=True):
        node_process = NodeProxyProcess(node_script=script)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required to start the Node upstream proxy"):
            node_process.start()


def test_start_errors_when_node_missing(tmp_path, monkeypatch):
    script = _create_node_script(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-node")
    monkeypatch.setenv("SKIP_DOTENV", "1")

    node_process = NodeProxyProcess(node_script=script)

    def raise_file_not_found(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("src.node.process.subprocess.Popen", raise_file_not_found)

    with pytest.raises(RuntimeError, match="Node.js runtime is not available in PATH"):
        node_process.start()


def test_stop_terminates_running_process(tmp_path):
    script = _create_node_script(tmp_path)
    node_process = NodeProxyProcess(node_script=script)
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    node_process._process = mock_proc

    node_process.stop()

    mock_proc.terminate.assert_called_once()
    mock_proc.wait.assert_called_once()
    assert node_process._process is None
