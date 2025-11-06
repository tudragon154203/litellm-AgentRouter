#!/usr/bin/env python3
"""Shared constants for middleware modules."""
from __future__ import annotations

# Endpoints where the proxy must strip the top-level `reasoning` parameter.
OPENAI_REASONING_FILTER_PATHS = frozenset({
    "/v1/chat/completions",
    "/chat/completions",
    "/v1/responses",
    "/responses",
})
