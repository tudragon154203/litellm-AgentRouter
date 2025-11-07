#!/usr/bin/env python3
"""
Middleware to enforce streaming control based on configuration.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .constants import STREAMING_CAPABLE_PATHS


class StreamingControlMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to enforce streaming control."""

    def __init__(self, app, allow_streaming: bool = True):
        """Initialize streaming control middleware.

        Args:
            app: FastAPI application instance
            allow_streaming: Whether to allow streaming requests (default: True)
        """
        super().__init__(app)
        self.allow_streaming = allow_streaming
        self.logger = logging.getLogger("litellm_launcher.streaming_control")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request and enforce streaming control if needed."""
        # Only process POST requests to streaming-capable endpoints
        if not self.allow_streaming and request.method == "POST" and request.url.path in STREAMING_CAPABLE_PATHS:
            client_request_id = request.headers.get("x-request-id")
            try:
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        payload = json.loads(body_bytes.decode("utf-8", errors="ignore"))
                    except json.JSONDecodeError:
                        payload = None

                    if isinstance(payload, dict) and payload.get("stream"):
                        # Force streaming to False
                        payload["stream"] = False
                        new_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

                        async def receive() -> dict[str, Any]:
                            return {"type": "http.request", "body": new_body, "more_body": False}

                        try:
                            # Replace request body/receiver for downstream handlers
                            request._body = new_body  # type: ignore[attr-defined]
                            request._receive = receive  # type: ignore[attr-defined]
                        except Exception:
                            pass

                        log_msg = {"action": "streaming_disabled", "original_stream": True, "enforced_stream": False}
                        if client_request_id:
                            log_msg["client_request_id"] = client_request_id
                        self.logger.debug(json.dumps(log_msg, separators=(",", ":")))
            except Exception:
                # Do not block request on filter errors
                pass

        return await call_next(request)
