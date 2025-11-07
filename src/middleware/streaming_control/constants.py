"""Constants for streaming control middleware."""

from __future__ import annotations

# OpenAI-compatible endpoints that support streaming
STREAMING_CAPABLE_PATHS = {
    "/chat/completions",
    "/v1/chat/completions",
    "/completions",
    "/v1/completions",
}
