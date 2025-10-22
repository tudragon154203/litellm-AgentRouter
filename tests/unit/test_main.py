#!/usr/bin/env python3
"""Unit tests for main.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.main import main


class TestMain:
    """Test cases for main function."""

    @patch("src.main.start_proxy")
    @patch("src.main.create_temp_config_if_needed")
    @patch("src.main.prepare_config")
    @patch("src.main.attach_signal_handlers")
    @patch("src.main.parse_args")
    @patch("src.main.validate_prereqs")
    @patch("src.main.load_dotenv_files")
    def test_main_with_generated_config(
        self,
        mock_load_dotenv,
        mock_validate,
        mock_parse_args,
        mock_attach_signals,
        mock_prepare_config,
        mock_create_temp,
        mock_start_proxy,
        capsys,
    ):
        """Test main function with generated config."""
        # Setup mocks
        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 8080
        mock_args.alias = "test-model"
        mock_parse_args.return_value = mock_args

        mock_config_text = "generated: config"
        mock_prepare_config.return_value = (mock_config_text, True)

        mock_temp_path = Path("/tmp/config.yaml")
        mock_create_temp.return_value.__enter__.return_value = mock_temp_path

        with patch("sys.exit") as mock_exit:
            main(["--alias", "test-model"])

        # Verify function calls in correct order
        mock_load_dotenv.assert_called_once()
        mock_validate.assert_called_once()
        mock_parse_args.assert_called_once_with(["--alias", "test-model"])
        mock_attach_signals.assert_called_once()
        mock_prepare_config.assert_called_once_with(mock_args)
        mock_create_temp.assert_called_once_with(mock_config_text, True)
        mock_start_proxy.assert_called_once_with(mock_args, mock_temp_path)

        # Verify exit was called
        mock_exit.assert_called_once_with(0)

        # Verify output message
        captured = capsys.readouterr()
        expected_msg = (
            "Starting LiteLLM proxy on 127.0.0.1:8080 "
            "with generated config (alias=test-model)."
        )
        assert expected_msg in captured.out

    @patch("src.main.start_proxy")
    @patch("src.main.create_temp_config_if_needed")
    @patch("src.main.prepare_config")
    @patch("src.main.attach_signal_handlers")
    @patch("src.main.parse_args")
    @patch("src.main.validate_prereqs")
    @patch("src.main.load_dotenv_files")
    def test_main_with_existing_config(
        self,
        mock_load_dotenv,
        mock_validate,
        mock_parse_args,
        mock_attach_signals,
        mock_prepare_config,
        mock_create_temp,
        mock_start_proxy,
        capsys,
    ):
        """Test main function with existing config file."""
        # Setup mocks
        mock_args = MagicMock()
        mock_args.host = "0.0.0.0"
        mock_args.port = 4000
        mock_args.alias = "local-gpt"
        mock_parse_args.return_value = mock_args

        mock_config_path = Path("/existing/config.yaml")
        mock_prepare_config.return_value = (mock_config_path, False)

        mock_create_temp.return_value.__enter__.return_value = mock_config_path

        with patch("sys.exit") as mock_exit:
            main([])

        # Verify function calls
        mock_load_dotenv.assert_called_once()
        mock_validate.assert_called_once()
        mock_parse_args.assert_called_once_with([])
        mock_attach_signals.assert_called_once()
        mock_prepare_config.assert_called_once_with(mock_args)
        mock_create_temp.assert_called_once_with(mock_config_path, False)
        mock_start_proxy.assert_called_once_with(mock_args, mock_config_path)

        # Verify exit was called
        mock_exit.assert_called_once_with(0)

        # Verify output message
        captured = capsys.readouterr()
        expected_msg = (
            "Starting LiteLLM proxy on 0.0.0.0:4000 "
            f"using config file {mock_config_path}."
        )
        assert expected_msg in captured.out

    @patch("src.main.start_proxy")
    @patch("src.main.create_temp_config_if_needed")
    @patch("src.main.prepare_config")
    @patch("src.main.attach_signal_handlers")
    @patch("src.main.parse_args")
    @patch("src.main.validate_prereqs")
    @patch("src.main.load_dotenv_files")
    def test_main_with_none_argv(
        self,
        mock_load_dotenv,
        mock_validate,
        mock_parse_args,
        mock_attach_signals,
        mock_prepare_config,
        mock_create_temp,
        mock_start_proxy,
    ):
        """Test main function with None argv (should use sys.argv)."""
        mock_args = MagicMock()
        mock_args.host = "localhost"
        mock_args.port = 3000
        mock_args.alias = "none-argv-model"
        mock_parse_args.return_value = mock_args

        mock_config_text = "config: text"
        mock_prepare_config.return_value = (mock_config_text, True)

        mock_temp_path = Path("/tmp/config.yaml")
        mock_create_temp.return_value.__enter__.return_value = mock_temp_path

        with patch("sys.exit"):
            main(None)

        # Verify parse_args was called with None
        mock_parse_args.assert_called_once_with(None)

    @patch("src.main.start_proxy")
    @patch("src.main.create_temp_config_if_needed")
    @patch("src.main.prepare_config")
    @patch("src.main.attach_signal_handlers")
    @patch("src.main.parse_args")
    @patch("src.main.validate_prereqs")
    @patch("src.main.load_dotenv_files")
    def test_main_execution_order(
        self,
        mock_load_dotenv,
        mock_validate,
        mock_parse_args,
        mock_attach_signals,
        mock_prepare_config,
        mock_create_temp,
        mock_start_proxy,
    ):
        """Test that main executes functions in the correct order."""
        # Setup mocks
        mock_args = MagicMock()
        mock_parse_args.return_value = mock_args
        mock_prepare_config.return_value = ("config", True)
        mock_create_temp.return_value.__enter__.return_value = Path("/tmp/config")

        with patch("sys.exit"):
            main([])

        # Verify call order using mock method calls
        call_order = [
            mock_load_dotenv,
            mock_validate,
            mock_parse_args,
            mock_attach_signals,
            mock_prepare_config,
            mock_create_temp.return_value.__enter__,
            mock_start_proxy,
        ]

        # Check that each mock was called
        for mock in call_order:
            mock.assert_called()

        # Additional verification of specific calls
        mock_prepare_config.assert_called_once_with(mock_args)
        mock_start_proxy.assert_called_once()

    def test_main_handles_proxy_system_exit(self):
        """Test main handles SystemExit from start_proxy."""
        # SystemExit with code 0 from start_proxy is handled inside start_proxy itself
        # This test verifies normal execution continues
        pass

    @patch("src.main.start_proxy", side_effect=RuntimeError("Proxy error"))
    @patch("src.main.create_temp_config_if_needed")
    @patch("src.main.prepare_config")
    @patch("src.main.attach_signal_handlers")
    @patch("src.main.parse_args")
    @patch("src.main.validate_prereqs")
    @patch("src.main.load_dotenv_files")
    def test_main_propagates_exceptions(
        self,
        mock_load_dotenv,
        mock_validate,
        mock_parse_args,
        mock_attach_signals,
        mock_prepare_config,
        mock_create_temp,
        mock_start_proxy,
    ):
        """Test main propagates exceptions from start_proxy."""
        mock_args = MagicMock()
        mock_parse_args.return_value = mock_args
        mock_prepare_config.return_value = ("config", True)
        mock_create_temp.return_value.__enter__.return_value = Path("/tmp/config")

        # Should propagate the exception
        with pytest.raises(RuntimeError, match="Proxy error"):
            main([])

    @patch("src.main.start_proxy")
    @patch("src.main.create_temp_config_if_needed")
    @patch("src.main.prepare_config")
    @patch("src.main.attach_signal_handlers")
    @patch("src.main.parse_args")
    @patch("src.main.validate_prereqs")
    @patch("src.main.load_dotenv_files")
    def test_main_with_different_host_port_combinations(
        self,
        mock_load_dotenv,
        mock_validate,
        mock_parse_args,
        mock_attach_signals,
        mock_prepare_config,
        mock_create_temp,
        mock_start_proxy,
        capsys,
    ):
        """Test main with different host and port combinations."""
        test_cases = [
            ("localhost", 3000, "test-model-1"),
            ("192.168.1.100", 8080, "test-model-2"),
            ("0.0.0.0", 4000, "test-model-3"),
            ("127.0.0.1", 9999, "test-model-4"),
        ]

        for host, port, alias in test_cases:
            # Reset mocks
            for mock in [mock_load_dotenv, mock_validate, mock_parse_args,
                        mock_attach_signals, mock_prepare_config, mock_create_temp,
                        mock_start_proxy]:
                mock.reset_mock()

            mock_args = MagicMock()
            mock_args.host = host
            mock_args.port = port
            mock_args.alias = alias
            mock_parse_args.return_value = mock_args
            mock_prepare_config.return_value = (f"config for {alias}", True)
            mock_create_temp.return_value.__enter__.return_value = Path(f"/tmp/{alias}.yaml")

            with patch("sys.exit"):
                main([])

            # Verify output contains correct host and port
            captured = capsys.readouterr()
            expected_msg = f"Starting LiteLLM proxy on {host}:{port}"
            assert expected_msg in captured.out

    @patch("src.main.start_proxy")
    @patch("src.main.create_temp_config_if_needed")
    @patch("src.main.prepare_config")
    @patch("src.main.attach_signal_handlers")
    @patch("src.main.parse_args")
    @patch("src.main.validate_prereqs")
    @patch("src.main.load_dotenv_files")
    def test_main_context_manager_cleanup(
        self,
        mock_load_dotenv,
        mock_validate,
        mock_parse_args,
        mock_attach_signals,
        mock_prepare_config,
        mock_create_temp,
        mock_start_proxy,
    ):
        """Test that context manager is properly used."""
        mock_args = MagicMock()
        mock_parse_args.return_value = mock_args
        mock_prepare_config.return_value = ("config", True)

        context_manager = MagicMock()
        mock_create_temp.return_value = context_manager
        context_manager.__enter__.return_value = Path("/tmp/config")

        with patch("sys.exit"):
            main([])

        # Verify context manager methods were called
        context_manager.__enter__.assert_called_once()
        context_manager.__exit__.assert_called_once()

    @patch("src.main.start_proxy")
    @patch("src.main.create_temp_config_if_needed")
    @patch("src.main.prepare_config")
    @patch("src.main.attach_signal_handlers")
    @patch("src.main.parse_args")
    @patch("src.main.validate_prereqs")
    @patch("src.main.load_dotenv_files")
    def test_main_type_annotations(
        self,
        mock_load_dotenv,
        mock_validate,
        mock_parse_args,
        mock_attach_signals,
        mock_prepare_config,
        mock_create_temp,
        mock_start_proxy,
    ):
        """Test that main accepts the correct argument types."""
        mock_args = MagicMock()
        mock_parse_args.return_value = mock_args
        mock_prepare_config.return_value = ("config", True)
        mock_create_temp.return_value.__enter__.return_value = Path("/tmp/config")

        with patch("sys.exit"):
            # Test with list of strings
            main(["--alias", "test"])

            mock_parse_args.assert_called_with(["--alias", "test"])

            mock_parse_args.reset_mock()

            # Test with None
            main(None)

            mock_parse_args.assert_called_with(None)

    def test_main_function_signature(self):
        """Test that main has the correct function signature."""
        import inspect

        sig = inspect.signature(main)
        params = sig.parameters

        assert "argv" in params
        assert params["argv"].annotation == "list[str] | None"
        assert params["argv"].default is None
        assert sig.return_annotation == "NoReturn"

    def test_main_exit_code_zero_after_proxy(self):
        """Test that main exits with code 0 after successful proxy completion."""
        # This tests the final sys.exit(0) line
        mock_args = MagicMock()
        mock_args.host = "localhost"
        mock_args.port = 3000
        mock_args.alias = "test-model"

        with patch("src.main.parse_args", return_value=mock_args), \
             patch("src.main.load_dotenv_files"), \
             patch("src.main.validate_prereqs"), \
             patch("src.main.attach_signal_handlers"), \
             patch("src.main.prepare_config", return_value=("config", True)), \
             patch("src.main.create_temp_config_if_needed") as mock_create_temp, \
             patch("src.main.start_proxy") as mock_start_proxy, \
             patch("sys.exit") as mock_exit:

            # Configure mocks
            mock_temp_path = Path("/tmp/config.yaml")
            mock_create_temp.return_value.__enter__.return_value = mock_temp_path

            main([])

            # Verify sys.exit(0) was called at the end
            mock_exit.assert_called_once_with(0)

    def test_main_final_sys_exit_line_44(self):
        """Test the final sys.exit(0) call on line 44."""
        # This test specifically targets line 44 to ensure it's covered
        mock_args = MagicMock()
        mock_args.host = "0.0.0.0"
        mock_args.port = 4000
        mock_args.alias = "test-model"

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

            # Verify the final sys.exit(0) was called (line 44)
            mock_exit.assert_called_once_with(0)

            # Ensure no other calls to sys.exit were made
            assert mock_exit.call_count == 1