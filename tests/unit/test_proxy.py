#!/usr/bin/env python3
"""Simplified unit tests for proxy.py - focusing on core functionality."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.proxy import start_proxy


class TestStartProxySimple:
    """Test cases for start_proxy function."""

    @patch("litellm.proxy.proxy_cli.run_server")
    def test_start_proxy_basic(self, mock_run_server):
        """Test start_proxy with basic arguments."""
        args = MagicMock()
        args.host = "127.0.0.1"
        args.port = 8080
        args.workers = 4
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/path/to/config.yaml")

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

    @patch("litellm.proxy.proxy_cli.run_server")
    def test_start_proxy_with_debug(self, mock_run_server):
        """Test start_proxy with debug enabled."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 3000
        args.workers = 1
        args.debug = True
        args.detailed_debug = False

        config_path = Path("/debug/config.yaml")

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

    @patch("litellm.proxy.proxy_cli.run_server")
    def test_start_proxy_system_exit_code_zero(self, mock_run_server):
        """Test that SystemExit with code 0 is not re-raised."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Simulate SystemExit with code 0 (normal termination)
        mock_run_server.main.side_effect = SystemExit(0)

        # Should not raise an exception
        start_proxy(args, config_path)

    @patch("litellm.proxy.proxy_cli.run_server")
    def test_start_proxy_system_exit_nonzero_reraises(self, mock_run_server):
        """Test that SystemExit with non-zero code is re-raised."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Simulate SystemExit with non-zero code (error)
        mock_run_server.main.side_effect = SystemExit(1)

        # Should re-raise the exception
        with pytest.raises(SystemExit) as exc_info:
            start_proxy(args, config_path)
        assert exc_info.value.code == 1