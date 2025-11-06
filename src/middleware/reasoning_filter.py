#!/usr/bin/env python3
"""
Middleware to strip top-level 'reasoning' parameter from OpenAI-style requests.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .constants import OPENAI_REASONING_FILTER_PATHS


class ReasoningFilterMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to remove top-level 'reasoning' from request body."""

    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("litellm_launcher.filter")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Only filter the supported OpenAI-compatible POST endpoints
        if request.method == "POST" and request.url.path in OPENAI_REASONING_FILTER_PATHS:
            client_request_id = request.headers.get("x-request-id")
            try:
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        payload = json.loads(body_bytes.decode("utf-8", errors="ignore"))
                    except json.JSONDecodeError:
                        payload = None
                    if isinstance(payload, dict) and "reasoning" in payload:
                        # Remove only top-level key
                        payload.pop("reasoning", None)
                        new_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

                        async def receive() -> dict[str, Any]:
                            return {"type": "http.request", "body": new_body, "more_body": False}

                        try:
                            # Replace request body/receiver for downstream handlers
                            request._body = new_body  # type: ignore[attr-defined]
                            request._receive = receive  # type: ignore[attr-defined]
                        except Exception:
                            pass

                        log_msg = {"dropped_param": "reasoning"}
                        if client_request_id:
                            log_msg["client_request_id"] = client_request_id
                        self.logger.debug(json.dumps(log_msg, separators=(",", ":")))
            except Exception:
                # Do not block request on filter errors
                pass

        return await call_next(request)
