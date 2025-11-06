#!/usr/bin/env python3
"""Edge tests for RuntimeConfig dotenv loader to hit warning/continue branches."""

from __future__ import annotations

from pathlib import Path

from src.config.config import RuntimeConfig


def test_dotenv_loader_skips_invalid_lines(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("""
# comment only
NO_EQUALS_LINE
VALID=ok
""".strip())
    monkeypatch.chdir(tmp_path)

    cfg = RuntimeConfig()
    cfg.ensure_loaded()

    # Should have loaded VALID, skipped others
    from os import getenv
    assert getenv("VALID") == "ok"
    assert getenv("NO_EQUALS_LINE") is None


def test_dotenv_loader_warning_on_read_failure(tmp_path, monkeypatch, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("VALID=ok\n")
    monkeypatch.chdir(tmp_path)

    # Force Path.read_text to raise to hit warning path
    def boom(self):
        raise RuntimeError("read failed")

    monkeypatch.setattr(Path, "read_text", boom)

    cfg = RuntimeConfig()
    cfg.ensure_loaded()

    captured = capsys.readouterr()
    assert "WARNING: failed to load" in captured.err
