#!/usr/bin/env python3
from __future__ import annotations

import logging
from typing import List

from .telemetry import TelemetryMiddleware
from .alias_lookup import create_alias_lookup
from .reasoning_filter import ReasoningFilterMiddleware
from ..config.models import ModelSpec

try:
    from ..utils import env_bool
except ImportError:  # pragma: no cover
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils import env_bool


def install_middlewares(app, model_specs: List[ModelSpec]) -> None:
    if not env_bool("TELEMETRY_ENABLE", True):
        logging.getLogger(__name__).info("Telemetry disabled; middlewares not installed")
        return
    alias_lookup = create_alias_lookup(model_specs) if model_specs else {}
    app.add_middleware(ReasoningFilterMiddleware)
    app.add_middleware(TelemetryMiddleware, alias_lookup=alias_lookup)
    app.state.litellm_telemetry_alias_lookup = alias_lookup
