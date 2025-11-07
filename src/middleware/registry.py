#!/usr/bin/env python3
from __future__ import annotations

from typing import List

from .telemetry.middleware import TelemetryMiddleware
from .telemetry.alias_lookup import create_alias_lookup
from .reasoning_filter.middleware import ReasoningFilterMiddleware
from .streaming_control.middleware import StreamingControlMiddleware
from ..config.models import ModelSpec
from ..utils import env_bool


def install_middlewares(app, model_specs: List[ModelSpec], allow_streaming: bool = True) -> None:
    # Telemetry is now configured explicitly via TelemetryConfig
    # Note: Middleware executes in reverse order, so we add telemetry first (runs last)
    alias_lookup = create_alias_lookup(model_specs) if model_specs else {}

    # Check TELEMETRY_ENABLE environment variable using centralized utility
    telemetry_enabled = env_bool("TELEMETRY_ENABLE", True)

    class EnvToggle:
        def enabled(self, request):
            return telemetry_enabled

    from .telemetry.config import TelemetryConfig
    from .telemetry.sinks.logger import LoggerSink

    # Default no-op reasoning policy
    class NoOpReasoningPolicy:
        def apply(self, request):
            return request, {}

    # Configure sinks if telemetry is enabled
    sinks = [LoggerSink()] if telemetry_enabled else []

    config = TelemetryConfig(
        toggle=EnvToggle(),
        alias_resolver=lambda alias: alias_lookup.get(alias, f"openai/{alias}"),
        sinks=sinks,
        reasoning_policy=NoOpReasoningPolicy(),
    )

    app.add_middleware(TelemetryMiddleware, config=config)
    app.state.litellm_telemetry_alias_lookup = alias_lookup

    # Always install ReasoningFilterMiddleware to drop unsupported 'reasoning' param
    # Added after telemetry so it runs before telemetry sees the request
    app.add_middleware(ReasoningFilterMiddleware)

    # Install StreamingControlMiddleware last so it runs first to enforce streaming policy
    # This ensures telemetry sees the modified streaming flag
    app.add_middleware(StreamingControlMiddleware, allow_streaming=allow_streaming)
