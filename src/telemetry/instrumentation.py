#!/usr/bin/env python3
"""
Instrumentation functionality for LiteLLM proxy telemetry.
"""

from __future__ import annotations

import logging
from typing import List

from .middleware import TelemetryMiddleware
from .alias_lookup import create_alias_lookup
from ..config.models import ModelSpec


def instrument_proxy_logging(model_specs: List[ModelSpec]) -> None:
    """Instrument LiteLLM proxy with telemetry middleware.

    This function should be called once per process to register the telemetry
    middleware with the LiteLLM FastAPI application.

    Args:
        model_specs: List of ModelSpec configurations for alias resolution
    """
    try:
        # Import LiteLLM proxy module
        from litellm.proxy import proxy_server

        # Get the app from proxy_server module
        if hasattr(proxy_server, 'app'):
            app = proxy_server.app
        else:
            return  # No app available, skip instrumentation

        if hasattr(app, 'state') and getattr(app.state, "_litellm_telemetry_installed", False):
            return  # Already instrumented, skip

        # Create alias lookup for telemetry
        alias_lookup = create_alias_lookup(model_specs) if model_specs else {}

        # Set up logger
        logger = logging.getLogger("litellm_launcher.telemetry")
        logger.setLevel(logging.INFO)

        # Register middleware
        app.add_middleware(TelemetryMiddleware, alias_lookup=alias_lookup)

        # Store alias lookup and installation flag in app state
        app.state.litellm_telemetry_alias_lookup = alias_lookup
        app.state._litellm_telemetry_installed = True

        logger.info("Telemetry middleware installed successfully")

    except Exception as e:
        # Log warning but continue with proxy startup
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to initialize telemetry logging: {e}")
