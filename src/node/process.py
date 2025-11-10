#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from ..config.config import runtime_config
from ..utils import build_user_agent


class NodeProxyProcess:
    """Manage the Node upstream proxy subprocess."""

    def __init__(self, node_script: Path | None = None):
        runtime_config.ensure_loaded()
        self._script_path = node_script or self._resolve_node_script()
        self._process: subprocess.Popen | None = None

    @staticmethod
    def _resolve_node_script() -> Path:
        base_dir = Path(__file__).resolve().parents[2]
        script = base_dir / "node" / "upstream-proxy.mjs"
        if not script.is_file():
            raise FileNotFoundError(f"Node upstream proxy script not found: {script}")
        return script

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("OPENAI_BASE_URL", runtime_config.get_str("OPENAI_BASE_URL", "https://agentrouter.org/v1"))
        api_key = runtime_config.get_str("OPENAI_API_KEY")
        if api_key:
            env.setdefault("OPENAI_API_KEY", api_key)
        env["NODE_USER_AGENT"] = build_user_agent()
        return env

    def start(self) -> subprocess.Popen:
        """Spawn the Node helper subprocess."""
        if self._process and self._process.poll() is None:
            return self._process

        if "OPENAI_API_KEY" not in os.environ and not runtime_config.get_str("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required to start the Node upstream proxy")

        env = self._build_env()
        try:
            self._process = subprocess.Popen(
                ["node", str(self._script_path)],
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Node.js runtime is not available in PATH") from exc

        return self._process

    def stop(self) -> None:
        """Terminate the Node helper subprocess if it is running."""
        if not self._process:
            return

        if self._process.poll() is not None:
            self._process = None
            return

        self._process.terminate()
        try:
            self._process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        finally:
            self._process = None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
