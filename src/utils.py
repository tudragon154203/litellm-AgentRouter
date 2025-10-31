#!/usr/bin/env python3
"""
Utility functions for LiteLLM proxy launcher.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_dotenv_files() -> None:
    """Load key-value pairs from .env files into the current environment."""
    def load_file(path: Path) -> None:
        if not path.is_file():
            return
        try:
            for raw_line in path.read_text().splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception as exc:
            print(f"WARNING: failed to load {path}: {exc}", file=sys.stderr)

    script_dir = Path(__file__).resolve().parent.parent
    cwd = Path.cwd()
    seen: set[Path] = set()
    for candidate in (script_dir / ".env", cwd / ".env"):
        if candidate not in seen:
            seen.add(candidate)
            load_file(candidate)


def quote(value: str) -> str:
    """Return a JSON-escaped string that is also valid YAML."""
    return json.dumps(value)


@contextmanager
def temporary_config(config_text: str) -> Iterator[Path]:
    """Persist a temporary config file for the lifetime of the context."""
    config_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="litellm-config-", delete=False
    )
    try:
        with config_file as handle:
            handle.write(config_text)
            handle.flush()
            path = Path(handle.name)
        yield path
    finally:
        try:
            Path(config_file.name).unlink(missing_ok=True)
        except Exception:
            pass


def attach_signal_handlers() -> None:
    """Attach signal handlers for graceful shutdown."""
    def handle_signal(signum, frame):  # pragma: no cover - runtime behaviour
        signame = signal.Signals(signum).name
        print(f"\nReceived {signame}, shutting down LiteLLM proxy...", file=sys.stderr)
        raise SystemExit(0)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)


def validate_prereqs() -> None:
    """Validate that required dependencies are available."""
    try:
        import litellm  # noqa: F401
        import litellm.proxy.proxy_cli  # noqa: F401
    except ImportError as exc:  # pragma: no cover - import error reported to user
        print(
            "ERROR: LiteLLM proxy dependencies are missing. "
            "Install them with `pip install 'litellm[proxy]'`.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
