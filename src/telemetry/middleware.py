#!/usr/bin/env python3
"""
Telemetry middleware for LiteLLM proxy request logging.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# GMT+7 timezone (Asia/Bangkok)
GMT7_TZ = timezone(timedelta(hours=7))


class TelemetryMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for logging chat completion telemetry."""

    def __init__(self, app, alias_lookup: Dict[str, str]):
        """Initialize telemetry middleware.

        Args:
            app: FastAPI application instance
            alias_lookup: Dictionary for model alias resolution
        """
        super().__init__(app)
        self.alias_lookup = alias_lookup
        self.logger = logging.getLogger("litellm_launcher.telemetry")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and emit telemetry log."""
        # Only process chat completion requests
        if request.method != "POST" or request.url.path != "/v1/chat/completions":
            return await call_next(request)

        start_time = time.perf_counter()

        # Extract request metadata
        remote_addr = self._get_remote_addr(request)
        client_request_id = request.headers.get("x-request-id")

        try:
            # Parse request body for model and streaming info
            request_body = await request.json()
            model_alias = request_body.get("model", "unknown")
            streaming = request_body.get("stream", False)
        except Exception:
            # If we can't parse request body, use defaults
            request_body = None
            model_alias = "unknown"
            streaming = False

        # Resolve upstream model
        app_state = getattr(getattr(request, "app", None), "state", None)
        alias_lookup = getattr(app_state, "litellm_telemetry_alias_lookup", self.alias_lookup)
        upstream_model = alias_lookup.get(model_alias, f"openai/{model_alias}")

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            # Extract telemetry data from response
            telemetry_data = await self._extract_response_telemetry(
                response=response,
                request_body=request_body,
                model_alias=model_alias,
                upstream_model=upstream_model,
                streaming=streaming,
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                client_request_id=client_request_id,
            )

            # Log telemetry
            self._log_telemetry(telemetry_data)

            return response

        except Exception as e:
            # Log error and re-raise
            error_telemetry = {
                "timestamp": datetime.now(GMT7_TZ).isoformat(),
                "remote_addr": remote_addr,
                "client_request_id": client_request_id,
                "model_alias": model_alias,
                "upstream_model": upstream_model,
                "streaming": streaming,
                "error": str(e),
                "success": False,
            }
            self._log_telemetry(error_telemetry)
            raise

    def _get_remote_addr(self, request: Request) -> Optional[str]:
        """Extract client IP address from request headers."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the forwarded chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # Fall back to client IP
        return getattr(request.client, "host", None) if request.client else None

    async def _extract_response_telemetry(
        self,
        response: Response,
        request_body: dict | None,
        model_alias: str,
        upstream_model: str,
        streaming: bool,
        duration_ms: float,
        remote_addr: str | None,
        client_request_id: str | None,
    ) -> Dict[str, Any]:
        """Extract telemetry data from response."""
        telemetry = {
            "timestamp": datetime.now(GMT7_TZ).isoformat(),
            "remote_addr": remote_addr,
            "client_request_id": client_request_id,
            "model_alias": model_alias,
            "upstream_model": upstream_model,
            "streaming": streaming,
            "duration_ms": round(duration_ms, 2),
            "success": True,
        }

        # Extract usage from response
        usage_data = await self._extract_usage_data(response, streaming)
        telemetry.update(usage_data)

        return telemetry

    async def _extract_usage_data(self, response: Response, streaming: bool) -> Dict[str, Any]:
        """Extract token usage data from response."""
        usage = {}

        try:
            if streaming:
                # For streaming responses, scan the response body for usage info
                usage = await self._extract_streaming_usage(response)
            else:
                # For non-streaming responses, parse JSON body
                response_body = response.body if hasattr(response, 'body') else None
                if response_body:
                    if isinstance(response_body, bytes):
                        response_text = response_body.decode('utf-8')
                    else:
                        response_text = str(response_body)

                    try:
                        response_json = json.loads(response_text)
                        if "usage" in response_json:
                            usage = response_json["usage"]
                    except (json.JSONDecodeError, KeyError):
                        pass

        except Exception:
            # If we can't extract usage data, leave it empty
            pass

        return {"usage": usage if usage else None}

    async def _extract_streaming_usage(self, response: Response) -> Dict[str, Any]:
        """Extract usage data from streaming response."""
        usage = {}

        try:
            # Try to get response body iterator
            if hasattr(response, 'body_iterator'):
                # Collect all chunks and look for usage data
                chunks = []
                async for chunk in response.body_iterator:
                    if isinstance(chunk, bytes):
                        chunks.append(chunk.decode('utf-8'))
                    else:
                        chunks.append(str(chunk))

                full_response = ''.join(chunks)

                # Look for usage in the final data message
                lines = full_response.split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            if "usage" in data:
                                usage = data["usage"]
                                break
                        except json.JSONDecodeError:
                            continue

        except Exception:
            pass

        return usage

    def _log_telemetry(self, telemetry_data: Dict[str, Any]) -> None:
        """Log telemetry data as JSON."""
        log_entry = json.dumps(telemetry_data, separators=(',', ':'))
        self.logger.info(f"TELEMETRY: {log_entry}")
