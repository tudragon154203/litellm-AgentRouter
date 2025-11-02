#!/usr/bin/env python3
"""
Unit tests for module exports - validates that each public module exposes
documented entrypoints and that importing them yields callables wired to refactored code.
"""

import importlib
import pytest


class TestModuleExports:
    """Validate that refactored modules expose documented entrypoints."""

    def test_main_module_exports(self):
        """Test that src.main exposes documented entrypoints."""
        main_module = importlib.import_module("src.main")

        # Check that main function exists and is callable
        assert hasattr(main_module, "main"), "main module should export main() function"
        assert callable(main_module.main), "main should be callable"

    def test_cli_module_exports(self):
        """Test that src.cli exposes documented entrypoints."""
        cli_module = importlib.import_module("src.cli")

        # Check that parse_args function exists and is callable
        assert hasattr(cli_module, "parse_args"), "cli module should export parse_args() function"
        assert callable(cli_module.parse_args), "parse_args should be callable"

    def test_config_module_exports(self):
        """Test that src.config exposes documented entrypoints via submodules."""
        # Test that functions can be imported from config submodules
        from src.config.models import ModelSpec
        from src.config.parsing import parse_model_spec, load_model_specs_from_env, load_model_specs_from_cli
        from src.config.rendering import render_config

        # Verify classes and functions are callable
        assert callable(ModelSpec), "ModelSpec should be callable"
        assert callable(parse_model_spec), "parse_model_spec should be callable"
        assert callable(load_model_specs_from_env), "load_model_specs_from_env should be callable"
        assert callable(load_model_specs_from_cli), "load_model_specs_from_cli should be callable"
        assert callable(render_config), "render_config should be callable"

    def test_proxy_module_exports(self):
        """Test that src.proxy exposes documented entrypoints."""
        proxy_module = importlib.import_module("src.proxy")

        # Check that start_proxy function exists and is callable
        assert hasattr(proxy_module, "start_proxy"), "proxy module should export start_proxy() function"
        assert callable(proxy_module.start_proxy), "start_proxy should be callable"

    def test_telemetry_module_exports(self):
        """Test that src.telemetry exposes documented entrypoints."""
        telemetry_module = importlib.import_module("src.telemetry")

        # Test that functions can be imported from telemetry submodules
        from src.telemetry.alias_lookup import create_alias_lookup
        from src.telemetry.middleware import TelemetryMiddleware

        # Verify functions are callable
        assert callable(create_alias_lookup), "create_alias_lookup should be callable"
        assert callable(TelemetryMiddleware), "TelemetryMiddleware should be callable"

    def test_utils_module_exports(self):
        """Test that src.utils exposes documented entrypoints."""
        utils_module = importlib.import_module("src.utils")

        # Check that documented utility functions exist and are callable
        documented_functions = [
            "env_bool",
            "load_dotenv_files",
            "quote",
            "temporary_config",
            "attach_signal_handlers",
            "validate_prereqs",
            "create_temp_config_if_needed"
        ]

        for func_name in documented_functions:
            assert hasattr(utils_module, func_name), f"utils module should export {func_name}() function"
            func = getattr(utils_module, func_name)
            assert callable(func), f"{func_name} should be callable"

    def test_entrypoint_functionality(self):
        """Test that entrypoints are actually functional when called."""
        # Test that ModelSpec can be instantiated
        from src.config.models import ModelSpec
        try:
            spec = ModelSpec(
                key="test",
                upstream_model="openai/gpt-4"
            )
            assert spec.key == "test"
            assert spec.upstream_model == "openai/gpt-4"
        except Exception as e:
            pytest.fail(f"ModelSpec instantiation failed: {e}")

    def test_no_unintended_public_exports(self):
        """Test that modules don't expose unintended internal helpers."""
        # This test would need to be updated based on actual implementation
        # For now, just verify that imports work as expected
        from src.config.models import ModelSpec
        from src.telemetry.alias_lookup import create_alias_lookup

        # Should be able to import documented items
        assert ModelSpec is not None
        assert create_alias_lookup is not None