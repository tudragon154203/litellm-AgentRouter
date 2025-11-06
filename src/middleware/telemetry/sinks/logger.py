#!/usr/bin/env python3
from __future__ import annotations

import json
import logging

from ..config import TelemetrySink


class LoggerSink(TelemetrySink):
    """Structured logger sink using json.dumps per user confirmation."""

    def __init__(self, name: str = "litellm.telemetry"):
        self.logger = logging.getLogger(name)
        if self.logger.level == logging.NOTSET:
            self.logger.setLevel(logging.INFO)
        if not self.logger.handlers and not logging.getLogger().handlers:
            # Ensure logger emits even if host hasn't configured logging yet
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            self.logger.addHandler(handler)

    def emit(self, event: Any) -> None:
        """Log serialized JSON event via INFO."""
        try:
            # Convert UsageTokens to dict for JSON serialization if needed
            event_dict = event
            if hasattr(event, '__dict__'):
                # For dataclasses, convert to dict for JSON serialization
                from ..events import UsageTokens
                if isinstance(event, UsageTokens):
                    event_dict = {
                        "total": event.total,
                        "prompt": event.prompt,
                        "completion": event.completion,
                        "reasoning": event.reasoning
                    }
                else:
                    event_dict = {k: v for k, v in event.__dict__.items() if not k.startswith('_')}

            serialized = json.dumps(event_dict, separators=(",", ":"))
            self.logger.info(serialized)
        except Exception as e:
            # Fallback to stringified representation if serialization fails
            self.logger.info(f"Failed to serialize event: {event}; error: {e}")
