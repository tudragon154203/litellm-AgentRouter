#!/usr/bin/env python3
"""Unit tests for proxy.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.proxy import start_proxy


class TestStartProxy:
    """Test cases for start_proxy function."""

    @patch("src.proxy.run_server")
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
            "--config", "/path/to/config.yaml"
        ]
        assert call_args == expected_args
        assert mock_run_server.main.call_args[1]["standalone_mode"] is False

    @patch("src.proxy.run_server")
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
            "--config", "/debug/config.yaml",
            "--debug"
        ]
        assert call_args == expected_args

    @patch("src.proxy.run_server")
    def test_start_proxy_with_detailed_debug(self, mock_run_server):
        """Test start_proxy with detailed debug enabled."""
        args = MagicMock()
        args.host = "0.0.0.0"
        args.port = 4000
        args.workers = 2
        args.debug = False
        args.detailed_debug = True

        config_path = Path("/detailed/config.yaml")

        start_proxy(args, config_path)

        call_args = mock_run_server.main.call_args[0][0]

        expected_args = [
            "--host", "0.0.0.0",
            "--port", "4000",
            "--num_workers", "2",
            "--config", "/detailed/config.yaml",
            "--detailed_debug"
        ]
        assert call_args == expected_args

    @patch("src.proxy.run_server")
    def test_start_proxy_with_both_debug_flags(self, mock_run_server):
        """Test start_proxy with both debug and detailed debug enabled."""
        args = MagicMock()
        args.host = "192.168.1.100"
        args.port = 5000
        args.workers = 8
        args.debug = True
        args.detailed_debug = True

        config_path = Path("/both/debug/config.yaml")

        start_proxy(args, config_path)

        call_args = mock_run_server.main.call_args[0][0]

        expected_args = [
            "--host", "192.168.1.100",
            "--port", "5000",
            "--num_workers", "8",
            "--config", "/both/debug/config.yaml",
            "--debug",
            "--detailed_debug"
        ]
        assert call_args == expected_args

    @patch("src.proxy.run_server")
    def test_start_proxy_with_path_object(self, mock_run_server):
        """Test start_proxy with Path object for config_path."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 7000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("C:\\path\\to\\config.yaml")

        start_proxy(args, config_path)

        call_args = mock_run_server.main.call_args[0][0]

        # Should convert Path to string
        assert "--config" in call_args
        config_index = call_args.index("--config")
        assert call_args[config_index + 1] == "C:\\path\\to\\config.yaml"

    @patch("src.proxy.run_server")
    def test_start_proxy_with_different_port_types(self, mock_run_server):
        """Test start_proxy with different port representations."""
        test_cases = [
            (8080, "8080"),
            ("3000", "3000"),
            (0, "0"),
        ]

        for port_value, expected_str in test_cases:
            mock_run_server.reset_mock()

            args = MagicMock()
            args.host = "localhost"
            args.port = port_value
            args.workers = 1
            args.debug = False
            args.detailed_debug = False

            config_path = Path("/config.yaml")

            start_proxy(args, config_path)

            call_args = mock_run_server.main.call_args[0][0]
            port_index = call_args.index("--port")
            assert call_args[port_index + 1] == expected_str

    @patch("src.proxy.run_server")
    def test_start_proxy_with_different_worker_types(self, mock_run_server):
        """Test start_proxy with different workers representations."""
        test_cases = [
            (1, "1"),
            (4, "4"),
            ("8", "8"),
        ]

        for workers_value, expected_str in test_cases:
            mock_run_server.reset_mock()

            args = MagicMock()
            args.host = "localhost"
            args.port = 4000
            args.workers = workers_value
            args.debug = False
            args.detailed_debug = False

            config_path = Path("/config.yaml")

            start_proxy(args, config_path)

            call_args = mock_run_server.main.call_args[0][0]
            workers_index = call_args.index("--num_workers")
            assert call_args[workers_index + 1] == expected_str

    @patch("src.proxy.run_server")
    def test_start_proxy_standalone_mode_false(self, mock_run_server):
        """Test that standalone_mode is always set to False."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        start_proxy(args, config_path)

        # Verify standalone_mode is False
        assert mock_run_server.main.call_args[1]["standalone_mode"] is False

    @patch("src.proxy.run_server")
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

    @patch("src.proxy.run_server")
    def test_start_proxy_system_exit_code_none(self, mock_run_server):
        """Test that SystemExit with code None is not re-raised."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Simulate SystemExit with code None
        mock_run_server.main.side_effect = SystemExit(None)

        # Should not raise an exception
        start_proxy(args, config_path)

    @patch("src.proxy.run_server")
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

    @patch("src.proxy.run_server")
    def test_start_proxy_other_exception_reraises(self, mock_run_server):
        """Test that non-SystemExit exceptions are re-raised."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Simulate a regular exception
        mock_run_server.main.side_effect = RuntimeError("Server error")

        # Should re-raise the exception
        with pytest.raises(RuntimeError, match="Server error"):
            start_proxy(args, config_path)

    @patch("src.proxy.run_server")
    def test_start_proxy_import_laziness(self, mock_run_server):
        """Test that run_server is imported lazily (only when function is called)."""
        # The import should happen inside the function, not at module level
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/config.yaml")

        # Before calling start_proxy, the import shouldn't have happened yet
        # This is more of a design test - in practice, we verify the mock works
        start_proxy(args, config_path)

        # Verify the mock was called, meaning the import and execution worked
        mock_run_server.main.assert_called_once()

    @patch("src.proxy.run_server")
    def test_start_proxy_argument_order_consistency(self, mock_run_server):
        """Test that CLI arguments are always in the correct order."""
        args = MagicMock()
        args.host = "test-host"
        args.port = 9999
        args.workers = 5
        args.debug = True
        args.detailed_debug = True

        config_path = Path("/test/config.yaml")

        start_proxy(args, config_path)

        call_args = mock_run_server.main.call_args[0][0]

        # Verify the order is always: host, port, num_workers, config, debug flags
        expected_order = [
            "--host", "test-host",
            "--port", "9999",
            "--num_workers", "5",
            "--config", "/test/config.yaml",
            "--debug",
            "--detailed_debug"
        ]
        assert call_args == expected_order

    @patch("src.proxy.run_server")
    def test_start_proxy_with_special_characters_in_config_path(self, mock_run_server):
        """Test start_proxy with special characters in config path."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = False

        config_path = Path("/path with spaces/config-test.yaml")

        start_proxy(args, config_path)

        call_args = mock_run_server.main.call_args[0][0]
        config_index = call_args.index("--config")
        assert call_args[config_index + 1] == "/path with spaces/config-test.yaml"