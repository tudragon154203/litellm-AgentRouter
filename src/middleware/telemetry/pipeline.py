#!/usr/bin/env python3
from __future__ import annotations

import logging
from typing import Any

from .config import TelemetrySink


class TelemetryPipeline:
    """Fan-out pipeline that emits events to all sinks with isolation."""

    def __init__(self, sinks: list[TelemetrySink]):
        self.sinks = sinks
        self.logger = logging.getLogger("litellm_launcher.telemetry.pipeline")

    def publish(self, event: Any) -> None:
        """Emit event to all configured sinks, isolating failures."""
        if not self.sinks:
            # No sinks configured; nothing to emit
            return

        for sink in self.sinks:
            try:
                sink.emit(event)
            except Exception as e:
                # Log sink failure but continue to other sinks
                self.logger.warning(f"Telemetry sink {sink.__class__.__name__} failed: {e}")
