#!/usr/bin/env python3
"""Covers main.py --print-config when config is generated (is_generated=True)."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch


def test_main_print_generated_config(monkeypatch):
    from src.main import main

    # Prepare argv with --print-config
    test_args = [
        "litellm-launcher",
        "--alias", "test-model",
        "--print-config",
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    # Patch parse_args to return object with print_config=True
    mock_args = SimpleNamespace(
        host="127.0.0.1",
        port=8080,
        alias="test-model",
        config=None,
        model_specs=[SimpleNamespace(alias="test-model", upstream_model="gpt-5")],
        print_config=True,
    )

    with patch("src.main.parse_args", return_value=mock_args), \
            patch("src.config.config.runtime_config.ensure_loaded"), \
            patch("src.main.validate_prereqs"), \
            patch("src.main.attach_signal_handlers"), \
            patch("src.main.prepare_config", return_value=("generated: true", True)):

        exit_called = []

        def mock_exit(code):
            exit_called.append(code)
            raise SystemExit(code)

        monkeypatch.setattr(sys, "exit", mock_exit)

        try:
            main()
        except SystemExit as e:
            assert e.code == 0

        # Ensure it exited with code 0 after printing generated config
        assert exit_called == [0]
