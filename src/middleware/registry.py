#!/usr/bin/env python3
from __future__ import annotations

from typing import List

from .telemetry.middleware import TelemetryMiddleware
from .alias_lookup import create_alias_lookup
from .reasoning_filter.middleware import ReasoningFilterMiddleware
from ..config.models import ModelSpec


def install_middlewares(app, model_specs: List[ModelSpec]) -> None:
    # Always install ReasoningFilterMiddleware to drop unsupported 'reasoning' param
    app.add_middleware(ReasoningFilterMiddleware)

    # Telemetry is now configured explicitly via TelemetryConfig (no env lookups)
    alias_lookup = create_alias_lookup(model_specs) if model_specs else {}
    # Provide a no-op toggle that always enables by default; callers should pass their own config

    class AlwaysOnToggle:
        def enabled(self, request):
            return True

    from .telemetry.config import TelemetryConfig

    # Default no-op reasoning policy
    class NoOpReasoningPolicy:
        def apply(self, request):
            return request, {}

    config = TelemetryConfig(
        toggle=AlwaysOnToggle(),
        alias_resolver=lambda alias: alias_lookup.get(alias, f"openai/{alias}"),
        sinks=[],  # Host app should provide sinks; default empty means no emissions
        reasoning_policy=NoOpReasoningPolicy(),
    )

    app.add_middleware(TelemetryMiddleware, config=config)
    app.state.litellm_telemetry_alias_lookup = alias_lookup
