#!/usr/bin/env python3
"""Additional test for proxy.py to achieve 100% coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.proxy import start_proxy


class TestStartProxyAppend:
    """Additional test cases for start_proxy to achieve 100% coverage."""

    @patch("litellm.proxy.proxy_cli.run_server")
    def test_start_proxy_detailed_debug_specific(self, mock_run_server):
        """Test that detailed_debug flag properly appends --detailed_debug (covers line 30)."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 4000
        args.workers = 1
        args.debug = False
        args.detailed_debug = True  # This should trigger line 30

        config_path = Path("/config.yaml")

        start_proxy(args, config_path)

        call_args = mock_run_server.main.call_args[0][0]

        # Verify --detailed_debug is specifically appended (covering line 30)
        assert "--detailed_debug" in call_args
        # It should be the last argument appended
        debug_index = call_args.index("--debug") if "--debug" in call_args else -1
        detailed_debug_index = call_args.index("--detailed_debug")
        assert detailed_debug_index > debug_index
