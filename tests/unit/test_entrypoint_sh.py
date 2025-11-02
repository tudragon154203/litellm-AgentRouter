#!/usr/bin/env python3
"""Unit tests for entrypoint.sh behavior (config generation and exec args).

These tests execute a TEMPORARILY patched copy of entrypoint.sh to:
- write into a temp app dir instead of /app
- intercept the final `exec` so the script doesn't start the server

Tests are skipped if bash/sed are not available or the OS isn't POSIX.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / "entrypoint.sh"

pytestmark = pytest.mark.skipif(
    os.name != "posix" or shutil.which("bash") is None or shutil.which("sed") is None,
    reason="Requires POSIX with bash and sed installed",
)


def _make_patched_entrypoint(tmp_path: Path, app_dir: Path) -> Path:
    """Create a temp copy of entrypoint.sh that writes to app_dir and intercepts exec."""
    original = ENTRYPOINT.read_text()
    # Replace hardcoded /app path with our temp app_dir
    script_body = original.replace("/app", app_dir.as_posix())

    # Intercept exec so we don't actually start the server; just echo the command
    wrapper = """#!/usr/bin/env bash
set -e
function exec() {
  echo EXEC "$@"
}
"""
    patched = wrapper + script_body
    out = tmp_path / "entrypoint_test.sh"
    out.write_text(patched)
    return out


def _run_script(script_path: Path, env: dict[str, str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["bash", str(script_path)],
        env=env,
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_generates_config_with_reasoning_effort(tmp_path: Path):
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    script = _make_patched_entrypoint(tmp_path, app_dir)

    env = os.environ.copy()
    env.update(
        {
            "PROXY_MODEL_KEYS": "primary",
            "MODEL_PRIMARY_UPSTREAM_MODEL": "gpt-5",
            "MODEL_PRIMARY_REASONING_EFFORT": "high",
            "OPENAI_API_KEY": "sk-test-123",
            "LITELLM_MASTER_KEY": "sk-test-master",
        }
    )

    code, out, err = _run_script(script, env)
    assert code == 0, f"script failed: {out}\n{err}"

    generated = (app_dir / "generated-config.yaml").read_text()
    assert 'model_name: "gpt-5"' in generated
    assert 'reasoning_effort: "high"' in generated
    assert 'master_key: "sk-test-master"' in generated

    assert "Starting LiteLLM proxy with configuration from environment variables..." in out
    assert "Generated config:" in out
    assert "***MASKED***" in out
    assert "sk-test-master" not in out

    assert "EXEC python -m src.main" in out
    assert "--config" in out
    assert "--host 0.0.0.0" in out
    assert "--port 4000" in out


def test_env_overrides_host_port_and_master_key(tmp_path: Path):
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    script = _make_patched_entrypoint(tmp_path, app_dir)

    env = os.environ.copy()
    env.update(
        {
            "PROXY_MODEL_KEYS": "primary",
            "MODEL_PRIMARY_UPSTREAM_MODEL": "gpt-5",
            "OPENAI_API_KEY": "sk-test-abc",
            "PORT": "8088",
            "LITELLM_HOST": "127.0.0.1",
            "LITELLM_MASTER_KEY": "sk-local-override",
        }
    )

    code, out, err = _run_script(script, env)
    assert code == 0, f"script failed: {out}\n{err}"

    config_text = (app_dir / "generated-config.yaml").read_text()
    assert 'master_key: "sk-local-override"' in config_text

    assert "--host 127.0.0.1" in out
    assert "--port 8088" in out


def test_fails_when_legacy_alias_present(tmp_path: Path):
    """Entrypoint should exit when legacy alias variables are defined."""
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    script = _make_patched_entrypoint(tmp_path, app_dir)

    env = os.environ.copy()
    env.update(
        {
            "PROXY_MODEL_KEYS": "gpt5",
            "MODEL_GPT5_ALIAS": "gpt-5",
            "MODEL_GPT5_UPSTREAM_MODEL": "gpt-5",
            "OPENAI_API_KEY": "sk-test-xyz",
        }
    )

    code, out, err = _run_script(script, env)
    assert code != 0
    assert "Legacy environment variable 'MODEL_GPT5_ALIAS' detected" in out or err
