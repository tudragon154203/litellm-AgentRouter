#!/usr/bin/env python3
"""Cover proxy.start_proxy branches and alias_lookup behavior."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.proxy import start_proxy
from src.middleware.telemetry.alias_lookup import create_alias_lookup
from src.config.models import ModelSpec


def test_create_alias_lookup_prefix_openai():
    specs = [
        ModelSpec(alias="a", upstream_model="gpt-5", key="a"),
        ModelSpec(alias="b", upstream_model="openai/gpt-4", key="b"),
    ]
    lookup = create_alias_lookup(specs)
    assert lookup["a"] == "openai/gpt-5"
    assert lookup["b"] == "openai/gpt-4"


def _install_fake_litellm_modules(monkeypatch):
    import types

    # Fake litellm.proxy.proxy_cli.run_server.main
    proxy_cli = types.ModuleType("litellm.proxy.proxy_cli")

    calls = {"main": []}

    def main(args, standalone_mode=False):
        calls["main"].append((args, standalone_mode))

    run_server = types.SimpleNamespace(main=main)
    proxy_cli.run_server = run_server

    # Fake litellm.proxy with proxy_server.app
    proxy_mod = types.ModuleType("litellm.proxy")
    proxy_mod.proxy_server = types.SimpleNamespace(app=MagicMock())

    monkeypatch.setitem(sys.modules, "litellm.proxy.proxy_cli", proxy_cli)
    monkeypatch.setitem(sys.modules, "litellm.proxy", proxy_mod)

    return calls


def test_start_proxy_windows_stream_wrapping(monkeypatch, tmp_path):
    calls = _install_fake_litellm_modules(monkeypatch)

    # Patch install_middlewares where imported from
    from src.middleware import registry as registry_mod
    monkeypatch.setattr(registry_mod, "install_middlewares", MagicMock())

    monkeypatch.setenv("PYTHONIOENCODING", "")
    monkeypatch.setattr(sys, "platform", "win32")

    # Mock stdout/stderr to have buffer via temporary wrapper objects
    class _W:
        def __init__(self):
            self.buffer = MagicMock()
    monkeypatch.setattr(sys, "stdout", _W(), raising=False)
    monkeypatch.setattr(sys, "stderr", _W(), raising=False)

    args = SimpleNamespace(host="localhost", port=1234, workers=1, debug=False, detailed_debug=False, model_specs=[])
    config_path = tmp_path / "c.yaml"
    config_path.write_text("x: y")

    start_proxy(args, config_path)

    # Middlewares installed
    assert registry_mod.install_middlewares.called
    # run_server.main called
    assert len(calls["main"]) == 1
    # PYTHONIOENCODING set to utf-8
    import os
    assert os.environ.get("PYTHONIOENCODING") == "utf-8"


def test_start_proxy_middleware_init_failure_logs_warning(caplog, monkeypatch, tmp_path):
    calls = _install_fake_litellm_modules(monkeypatch)

    # Force install_middlewares to raise
    from src.middleware import registry as registry_mod
    monkeypatch.setattr(registry_mod, "install_middlewares", MagicMock(side_effect=RuntimeError("boom")))

    args = SimpleNamespace(host="localhost", port=1234, workers=1, debug=True, detailed_debug=True, model_specs=[])
    config_path = tmp_path / "c.yaml"
    config_path.write_text("x: y")

    with caplog.at_level("WARNING"):
        start_proxy(args, config_path)

    # Ensure warning logged
    assert any("Failed to initialize middlewares" in r.message for r in caplog.records)
    assert len(calls["main"]) == 1
