#!/usr/bin/env python3
"""Test for main.py - accepting 99% coverage as the remaining line is the main guard."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from src.main import main


class TestMainGuard:
    """Test main function to achieve maximum coverage."""

    def test_main_complete_execution_flow(self):
        """Test complete main execution flow to maximize coverage."""
        # Mock sys.argv to simulate command line execution
        original_argv = sys.argv[:]
        sys.argv = ['script_name']

        try:
            mock_args = type('Args', (), {
                'host': 'localhost', 'port': 4000, 'alias': 'test-model'
            })()

            with patch("src.main.parse_args", return_value=mock_args), \
                    patch("src.main.load_dotenv_files"), \
                    patch("src.main.validate_prereqs"), \
                    patch("src.main.attach_signal_handlers"), \
                    patch("src.main.prepare_config", return_value=("config", True)), \
                    patch("src.main.create_temp_config_if_needed") as mock_create_temp, \
                    patch("src.main.start_proxy"), \
                    patch("sys.exit") as mock_exit:

                # Configure mocks to simulate successful execution
                mock_temp_path = Path("/tmp/config.yaml")
                mock_create_temp.return_value.__enter__.return_value = mock_temp_path

                # Execute main function
                main([])

                # Verify the final sys.exit(0) was called
                mock_exit.assert_called_once_with(0)

        finally:
            # Restore original sys.argv
            sys.argv = original_argv
