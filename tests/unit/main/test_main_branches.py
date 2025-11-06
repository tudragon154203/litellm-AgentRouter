#!/usr/bin/env python3
from __future__ import annotations

import sys
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.main import main


class TestMainBranches:
    """Test uncovered branches in main module."""

    def test_main_print_config_exits(self):
        """main should exit after printing config."""
        with patch("sys.argv", ["main.py", "--print-config"]):
            with patch("src.main.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.print_config = True
                mock_parse.return_value = mock_args

                with patch("src.main.prepare_config") as mock_prepare:
                    mock_prepare.return_value = ("config: test", True)

                    with patch("sys.exit") as mock_exit:
                        with patch("builtins.print") as mock_print:
                            main()

                            # Should print config
                            mock_print.assert_called()
                            # Should exit with 0
                            mock_exit.assert_called_with(0)

    def test_main_normal_flow_exits_after_proxy(self):
        """main should exit with 0 after proxy completes."""
        with patch("sys.argv", ["main.py"]):
            with patch("src.main.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.print_config = False
                mock_parse.return_value = mock_args

                with patch("src.main.prepare_config") as mock_prepare:
                    mock_prepare.return_value = ("config: test", True)

                    with patch("src.main.create_temp_config_if_needed") as mock_temp:
                        mock_temp.return_value.__enter__ = MagicMock(return_value=Path("/tmp/config.yaml"))
                        mock_temp.return_value.__exit__ = MagicMock(return_value=False)

                        with patch("src.main.start_proxy") as mock_start:
                            with patch("sys.exit") as mock_exit:
                                with patch("src.main.get_startup_message", return_value="Starting..."):
                                    main()

                                    # Should start proxy
                                    mock_start.assert_called_once()
                                    # Should exit with 0
                                    mock_exit.assert_called_with(0)
