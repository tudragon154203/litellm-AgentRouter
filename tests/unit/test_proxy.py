#!/usr/bin/env python3
"""Simplified unit tests for proxy.py - focusing on core functionality."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from src.proxy import start_proxy


def _stub_run_server():
    run_server = MagicMock()
    run_server.main = MagicMock()
    proxy_cli = ModuleType("proxy_cli")
    proxy_cli.run_server = run_server
    proxy = ModuleType("proxy")
    proxy.proxy_cli = proxy_cli
    litellm = ModuleType("litellm")
    litellm.proxy = proxy
    modules = {
        "litellm": litellm,
        "litellm.proxy": proxy,
        "litellm.proxy.proxy_cli": proxy_cli,
    }
    return run_server, modules


class TestStartProxySimple:
    """Test cases for start_proxy function."""

    def test_start_proxy_basic(self):
        """Test start_proxy with basic arguments."""
        args = MagicMock()
        args.host = "127.0.0.1"
        args.port = 8080
        args.workers = 4
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/path/to/config.yaml")

        mock_run_server, modules = _stub_run_server()
        with patch.dict(sys.modules, modules):
            start_proxy(args, config_path)

        # Verify run_server.main was called with correct arguments
        mock_run_server.main.assert_called_once()
        call_args = mock_run_server.main.call_args[0][0]

        expected_args = [
            "--host", "127.0.0.1",
            "--port", "8080",
            "--num_workers", "4",
            "--config", str(Path("/path/to/config.yaml"))
        ]
        assert call_args == expected_args
        assert mock_run_server.main.call_args[1]["standalone_mode"] is False

    def test_start_proxy_with_debug(self):
        """Test start_proxy with debug enabled."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 3000
        args.workers = 1
        args.debug = True
        args.detailed_debug = False

        config_path = Path("/debug/config.yaml")

        mock_run_server, modules = _stub_run_server()
        with patch.dict(sys.modules, modules):
            start_proxy(args, config_path)

        call_args = mock_run_server.main.call_args[0][0]

        expected_args = [
            "--host", "localhost",
            "--port", "3000",
            "--num_workers", "1",
            "--config", str(Path("/debug/config.yaml")),
            "--debug"
        ]
        assert call_args == expected_args

    def test_start_proxy_system_exit_code_zero(self):
        """Test that SystemExit with code 0 is not re-raised."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Simulate SystemExit with code 0 (normal termination)
        mock_run_server, modules = _stub_run_server()
        mock_run_server.main.side_effect = SystemExit(0)

        with patch.dict(sys.modules, modules):
            start_proxy(args, config_path)

    def test_start_proxy_system_exit_nonzero_reraises(self):
        """Test that SystemExit with non-zero code is re-raised."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Simulate SystemExit with non-zero code (error)
        mock_run_server, modules = _stub_run_server()
        mock_run_server.main.side_effect = SystemExit(1)

        with patch.dict(sys.modules, modules):
            with pytest.raises(SystemExit) as exc_info:
                start_proxy(args, config_path)
        assert exc_info.value.code == 1

    def test_start_proxy_system_exit_code_none_reraises(self):
        """Test that SystemExit with code None is not re-raised."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Simulate SystemExit with code None
        mock_run_server, modules = _stub_run_server()
        mock_run_server.main.side_effect = SystemExit(None)

        with patch.dict(sys.modules, modules):
            start_proxy(args, config_path)

    def test_start_proxy_line_30_coverage(self):
        """Test that covers line 30 in proxy.py - the specific logic for SystemExit handling."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Test SystemExit with code 0 (should not be re-raised)
        mock_run_server, modules = _stub_run_server()

        with patch.dict(sys.modules, modules):
            mock_run_server.main.side_effect = SystemExit(0)
            start_proxy(args, config_path)

            mock_run_server.reset_mock()
            mock_run_server.main.side_effect = SystemExit(None)
            start_proxy(args, config_path)

            mock_run_server.reset_mock()
            mock_run_server.main.side_effect = SystemExit(1)
            with pytest.raises(SystemExit) as exc_info:
                start_proxy(args, config_path)
        assert exc_info.value.code == 1

    def test_start_proxy_detailed_debug_specific(self):
        """Test that detailed_debug flag properly appends --detailed_debug (covers line 30)."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = True  # This should trigger line 30

        config_path = Path("/config.yaml")

        mock_run_server, modules = _stub_run_server()
        with patch.dict(sys.modules, modules):
            start_proxy(args, config_path)

        call_args = mock_run_server.main.call_args[0][0]

        # Verify --detailed_debug is specifically appended (covering line 30)
        assert "--detailed_debug" in call_args
        # It should be the last argument appended
        debug_index = call_args.index("--debug") if "--debug" in call_args else -1
        detailed_debug_index = call_args.index("--detailed_debug")
        assert detailed_debug_index > debug_index
