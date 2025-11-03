#!/usr/bin/env python3
"""
Telemetry middleware for LiteLLM proxy request logging.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator, Dict, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Import env_bool with absolute path to avoid relative import issues
try:
    from ..utils import env_bool  # Relative import when running as part of package
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils import env_bool  # Absolute import as fallback


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
        # Check if telemetry is disabled via environment variable
        if not env_bool("TELEMETRY_ENABLE", True):
            return await call_next(request)

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
            telemetry_data, processed_response = await self._extract_response_telemetry(
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

            return processed_response

        except Exception as e:
            # Log error and re-raise
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            status_code = getattr(e, "status_code", 500)
            error_telemetry = {
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "streaming": streaming,
                "upstream_model": upstream_model,
                "prompt_tokens": None,
                "completion_tokens": None,
                "reasoning_tokens": None,
                "total_tokens": None,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            if client_request_id:
                error_telemetry["client_request_id"] = client_request_id
            self._log_telemetry(error_telemetry)
            raise

    def _get_remote_addr(self, request: Request) -> str:
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
        if request.client and hasattr(request.client, "host"):
            return request.client.host

        return "unknown"

    async def _extract_response_telemetry(
        self,
        response: Any,
        request_body: dict | None,
        model_alias: str,
        upstream_model: str,
        streaming: bool,
        duration_ms: float,
        remote_addr: str,
        client_request_id: str | None,
    ) -> Tuple[Dict[str, Any], Any]:
        """Extract telemetry data from response per PRD specification."""
        status_code = getattr(response, "status_code", 200)
        telemetry: Dict[str, Any] = {
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "streaming": streaming,
            "upstream_model": upstream_model,
            "prompt_tokens": None,
            "completion_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
            "error_type": None,
            "error_message": None,
        }

        if client_request_id:
            telemetry["client_request_id"] = client_request_id

        processed_response, usage_data, parse_error = await self._extract_usage_data(response, streaming)

        if usage_data:
            telemetry["prompt_tokens"] = usage_data.get("prompt_tokens")
            telemetry["completion_tokens"] = usage_data.get("completion_tokens")
            telemetry["total_tokens"] = usage_data.get("total_tokens")

            output_details = usage_data.get("output_token_details", {})
            if output_details:
                telemetry["reasoning_tokens"] = output_details.get("reasoning_tokens")
        else:
            telemetry["missing_usage"] = True

        if parse_error:
            telemetry["parse_error"] = True

        return telemetry, processed_response

    def _parse_usage_from_response(self, response_json: dict) -> dict | None:
        """Parse usage data from response JSON.

        Args:
            response_json: Parsed response JSON

        Returns:
            Usage dictionary with normalized field names or None if not found
        """
        usage = response_json.get("usage")
        if not usage:
            return None

        # Normalize field names (handle both OpenAI and Anthropic conventions)
        normalized = {}

        # Handle prompt tokens (input_tokens or prompt_tokens)
        normalized["prompt_tokens"] = usage.get("prompt_tokens") or usage.get("input_tokens", 0)

        # Handle completion tokens (output_tokens or completion_tokens)
        normalized["completion_tokens"] = usage.get("completion_tokens") or usage.get("output_tokens", 0)

        # Calculate total if missing
        if "total_tokens" in usage:
            normalized["total_tokens"] = usage["total_tokens"]
        else:
            normalized["total_tokens"] = normalized["prompt_tokens"] + normalized["completion_tokens"]

        # Preserve output_token_details if present
        if "output_token_details" in usage:
            normalized["output_token_details"] = usage["output_token_details"]

        return normalized

    async def _extract_usage_data(
        self,
        response: Any,
        streaming: bool,
    ) -> Tuple[Any, Dict[str, Any] | None, bool]:
        """Extract token usage data from response."""
        usage: Dict[str, Any] | None = None
        parse_error = False
        processed_response = response

        try:
            if streaming:
                processed_response, usage = await self._extract_streaming_usage(response)
            else:
                response_body = getattr(response, "body", None)

                if response_body:
                    if isinstance(response_body, bytes):
                        response_text = response_body.decode("utf-8", errors="ignore")
                    else:
                        response_text = str(response_body)

                    try:
                        response_json = json.loads(response_text)
                    except json.JSONDecodeError:
                        parse_error = True
                    else:
                        usage = self._parse_usage_from_response(response_json)
        except Exception:
            parse_error = False

        return processed_response, usage, parse_error

    async def _extract_streaming_usage(self, response: Any) -> Tuple[Any, Dict[str, Any] | None]:
        """Extract usage data from streaming response."""
        usage: Dict[str, Any] | None = None
        chunks: list[Any] = []

        async def consume(iterator: AsyncIterator[Any]) -> None:
            nonlocal usage
            async for chunk in iterator:
                chunks.append(chunk)

                if usage is None:
                    chunk_text = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, bytes) else str(chunk)
                    usage = self._parse_usage_from_stream_chunk(chunk_text)

        try:
            if hasattr(response, "body_iterator"):
                await consume(response.body_iterator)
                response.body_iterator = self._replay_stream_chunks(chunks)
                replayable = response
            elif hasattr(response, "__aiter__"):
                await consume(response)
                replayable = self._replay_stream_chunks(chunks)
            else:
                replayable = response
        except Exception:
            replayable = response

        return replayable, usage

    def _parse_usage_from_stream_chunk(self, chunk_text: str) -> Dict[str, Any] | None:
        """Attempt to extract usage information from a streaming chunk."""
        for line in chunk_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped == "data: [DONE]":
                continue

            if stripped.startswith("data:"):
                payload_text = stripped[5:].strip()
                if not payload_text or payload_text == "[DONE]":
                    continue
                try:
                    payload = json.loads(payload_text)
                except json.JSONDecodeError:
                    continue
                usage = self._parse_usage_from_response(payload)
                if usage:
                    return usage

        try:
            payload = json.loads(chunk_text)
        except json.JSONDecodeError:
            return None

        return self._parse_usage_from_response(payload)

    def _replay_stream_chunks(self, chunks: list[Any]) -> AsyncIterator[Any]:
        """Create a replayable async iterator for consumed streaming chunks."""

        async def iterator() -> AsyncIterator[Any]:
            for chunk in chunks:
                yield chunk

        return iterator()

    def _log_telemetry(self, telemetry_data: Dict[str, Any]) -> None:
        """Log telemetry data as JSON per PRD specification."""
        log_entry = json.dumps(telemetry_data, separators=(',', ':'))
        self.logger.info(log_entry)
