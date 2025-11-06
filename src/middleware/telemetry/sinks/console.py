#!/usr/bin/env python3
from __future__ import annotations

import sys

from ..config import TelemetrySink


class ConsoleSink(TelemetrySink):
    """Simple console output sink; useful for debugging or demos per PRD."""

    def emit(self, event: Any) -> None:
        """Write event to stdout."""
        # Write directly to sys.stdout to avoid interference with logging config
        print(event)
