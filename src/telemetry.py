#!/usr/bin/env python3
"""
Request telemetry logging middleware for LiteLLM proxy.

Provides structured JSON logging for chat completion requests including
model usage, latency, and error information.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import ModelSpec

# GMT+7 timezone (Asia/Bangkok)
GMT7_TZ = timezone(timedelta(hours=7))


def create_alias_lookup(model_specs: List[ModelSpec]) -> Dict[str, str]:
    """Create a lookup dictionary for model alias → upstream model resolution.

    Args:
        model_specs: List of ModelSpec configurations

    Returns:
        Dictionary mapping alias names to upstream model names (with openai/ prefix)
    """
    lookup = {}
    for spec in model_specs:
        # Ensure upstream_model has openai/ prefix
        upstream_model = spec.upstream_model
        if not upstream_model.startswith("openai/"):
            upstream_model = f"openai/{upstream_model}"
        lookup[spec.alias] = upstream_model
    return lookup


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
                remote_addr=remote_addr,
                client_request_id=client_request_id,
                duration_ms=duration_ms,
                start_time=start_time
            )

        except Exception as exc:
            # Handle request processing errors
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            # Extract status code from exception if available
            status_code = getattr(exc, 'status_code', 500)

            telemetry_data = {
                "event": "chat_completion",
                "timestamp": datetime.now(GMT7_TZ).isoformat(),
                "remote_addr": remote_addr,
                "path": "/v1/chat/completions",
                "method": "POST",
                "status_code": status_code,
                "duration_ms": duration_ms,
                "streaming": streaming,
                "request_id": None,
                "model_alias": model_alias,
                "upstream_model": upstream_model,
                "prompt_tokens": None,
                "completion_tokens": None,
                "reasoning_tokens": None,
                "total_tokens": None,
                "error_type": type(exc).__name__,
                "error_message": self._sanitize_error_message(str(exc)),
                "parse_error": False,
                "client_request_id": client_request_id,
            }

            # Re-raise exception after logging
            self._log_telemetry(telemetry_data)
            raise

        # Log successful request telemetry
        self._log_telemetry(telemetry_data)
        return response

    async def _extract_response_telemetry(
        self,
        response,
        request_body: Optional[Dict],
        model_alias: str,
        upstream_model: str,
        streaming: bool,
        remote_addr: str,
        client_request_id: Optional[str],
        duration_ms: float,
        start_time: float
    ) -> Dict[str, Any]:
        """Extract telemetry data from response."""
        telemetry_data = {
            "event": "chat_completion",
            "timestamp": datetime.now(GMT7_TZ).isoformat(),
            "remote_addr": remote_addr,
            "path": "/v1/chat/completions",
            "method": "POST",
            "status_code": getattr(response, 'status_code', 200),
            "duration_ms": duration_ms,
            "streaming": streaming,
            "request_id": None,
            "model_alias": model_alias,
            "upstream_model": upstream_model,
            "prompt_tokens": None,
            "completion_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
            "error_type": None,
            "error_message": None,
            "parse_error": False,
            "client_request_id": client_request_id,
        }

        # Handle different response types
        content_type = (getattr(response, 'headers', {}) or {}).get('content-type') if hasattr(response, 'headers') else None
        is_event_stream = isinstance(content_type, str) and 'text/event-stream' in content_type.lower()
        if streaming or is_event_stream:
            # For streaming/SSE responses, intercept generator
            reconstructed_response, usage_data = await self._extract_streaming_usage(response)
            telemetry_data.update(usage_data)
            response = reconstructed_response
        elif hasattr(response, 'body_iterator') and not is_event_stream:
            # Some OpenAPI JSON responses are delivered via body_iterator
            reconstructed_response, usage_data = await self._extract_streaming_usage(response)
            telemetry_data.update(usage_data)
            response = reconstructed_response
        else:
            # For non-streaming responses, parse body
            try:
                response_body = json.loads(response.body.decode()) if hasattr(response, 'body') and response.body else {}
                usage_data = self._parse_usage_from_response(response_body)
                telemetry_data.update(usage_data)
                telemetry_data["request_id"] = response_body.get("id")
            except Exception as e:
                self.logger.debug(f"Failed to parse response body: {e}")
                telemetry_data["parse_error"] = True

        # Check if usage data is missing
        if all(telemetry_data[key] is None for key in ["prompt_tokens", "completion_tokens", "total_tokens"]):
            telemetry_data["missing_usage"] = True

        return telemetry_data

    async def _extract_streaming_usage(self, response):
        """Extract usage information from streaming response."""
        usage_data = {
            "prompt_tokens": None,
            "completion_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
            "request_id": None,
        }

        reconstructed_response = response

        try:
            # Handle different types of streaming responses
            if hasattr(response, '__aiter__'):
                # Async generator case - consume all chunks and reconstruct
                body_content = b""
                chunks = []
                async for chunk in response:
                    chunks.append(chunk)
                    if isinstance(chunk, str):
                        body_content += chunk.encode()
                    else:
                        body_content += chunk

                # Try parsing as SSE first
                text = body_content.decode(errors="ignore")
                usage_found = self._parse_usage_from_sse(text)
                if usage_found:
                    usage_data.update(usage_found)
                else:
                    # Fallback: if it's plain JSON, parse usage directly
                    text_stripped = text.lstrip()
                    if text_stripped.startswith("{") or text_stripped.startswith("["):
                        try:
                            response_body = json.loads(text_stripped)
                            if isinstance(response_body, dict):
                                usage_data.update(self._parse_usage_from_response(response_body))
                                usage_data["request_id"] = response_body.get("id")
                        except Exception:
                            pass

                # Return reconstructed generator
                reconstructed_response = self._create_async_iter(chunks)

            elif hasattr(response, 'body_iterator'):
                # StreamingResponse case (can also carry JSON with chunked transfer)
                body_content = b""
                async for chunk in response.body_iterator:
                    body_content += chunk

                text = body_content.decode(errors="ignore")
                usage_found = self._parse_usage_from_sse(text)
                if usage_found:
                    usage_data.update(usage_found)
                else:
                    # Fallback: try to parse as plain JSON body
                    text_stripped = text.lstrip()
                    if text_stripped.startswith("{") or text_stripped.startswith("["):
                        try:
                            response_body = json.loads(text_stripped)
                            if isinstance(response_body, dict):
                                usage_data.update(self._parse_usage_from_response(response_body))
                                usage_data["request_id"] = response_body.get("id")
                        except Exception:
                            pass

                # Reconstruct response
                response.body_iterator = self._create_async_iter([body_content])
                reconstructed_response = response

        except Exception as e:
            # If we can't parse streaming usage, that's okay
            self.logger.debug(f"Failed to extract streaming usage: {e}")

        return reconstructed_response, usage_data

    def _parse_usage_from_sse(self, sse_data: str) -> Optional[Dict[str, Any]]:
        """Parse usage information from Server-Sent Events data."""
        usage_data = None

        for line in sse_data.split('\n'):
            if line.startswith('data: ') and not line.startswith('data: [DONE]'):
                try:
                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                    if 'usage' in data:
                        usage_info = data['usage']
                        parsed_usage = {
                            "prompt_tokens": usage_info.get("prompt_tokens"),
                            "completion_tokens": usage_info.get("completion_tokens"),
                            "total_tokens": usage_info.get("total_tokens"),
                            "request_id": data.get("id"),
                        }
                        # Extract reasoning tokens if present
                        output_details = usage_info.get("output_token_details", {})
                        if output_details and "reasoning_tokens" in output_details:
                            parsed_usage["reasoning_tokens"] = output_details["reasoning_tokens"]
                        usage_data = parsed_usage
                        break
                except json.JSONDecodeError:
                    continue

        return usage_data

    def _parse_usage_from_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        """Parse usage information from response body.

        Supports multiple provider shapes:
        - OpenAI: usage.prompt_tokens, usage.completion_tokens, usage.total_tokens
        - Alt providers: usage.input_tokens/output_tokens/total_tokens
        - Reasoning tokens: usage.output_token_details.reasoning_tokens OR
          usage.completion_tokens_details.reasoning_tokens
        """
        usage = response_body.get("usage", {}) or {}

        # Try canonical OpenAI keys first
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")

        # Fallback to alternative key names commonly used by providers
        if prompt_tokens is None:
            prompt_tokens = usage.get("input_tokens")
        if completion_tokens is None:
            completion_tokens = usage.get("output_tokens")
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            try:
                total_tokens = int(prompt_tokens) + int(completion_tokens)
            except Exception:
                pass

        parsed_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

        # Extract reasoning tokens from known locations
        reasoning_tokens = None
        output_details = usage.get("output_token_details", {}) or {}
        if "reasoning_tokens" in output_details:
            reasoning_tokens = output_details.get("reasoning_tokens")
        else:
            completion_details = usage.get("completion_tokens_details", {}) or {}
            if "reasoning_tokens" in completion_details:
                reasoning_tokens = completion_details.get("reasoning_tokens")
        if reasoning_tokens is not None:
            parsed_usage["reasoning_tokens"] = reasoning_tokens

        return parsed_usage

    def _get_remote_addr(self, request: Request) -> str:
        """Extract remote address from request."""
        # Try client IP first, then proxy IP
        client = request.client
        if client:
            return f"{client.host}:{client.port}"

        # Fallback to headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return "unknown"

    def _sanitize_error_message(self, message: str) -> str:
        """Sanitize error message to remove sensitive information."""
        import re
        # Remove API keys and other sensitive patterns
        patterns = [
            r'(Bearer\s+)[a-zA-Z0-9\-_\.]+',
            r'(api[_-]?key["\s]*[:=]\s*)["\']?[a-zA-Z0-9\-_\.]+["\']?',
            r'(sk-[a-zA-Z0-9]{48})',
            r'(Authorization\s*:\s*Bearer\s+[a-zA-Z0-9\-_\.]+)',
        ]

        sanitized = message
        for pattern in patterns:
            sanitized = re.sub(pattern, r'\1: [REDACTED]', sanitized)

        return sanitized

    def _log_telemetry(self, telemetry_data: Dict[str, Any]) -> None:
        """Log telemetry data with limited fields."""
        try:
            # Remove fields per specification: event, timestamp, remote_addr, path, method, request_id, model_alias
            filtered_data = {
                key: value for key, value in telemetry_data.items()
                if key not in ["event", "timestamp", "remote_addr", "path", "method", "request_id", "model_alias"]
            }
            log_message = json.dumps(filtered_data, separators=(',', ':'))
            self.logger.info(log_message)
        except Exception as e:
            # If logging fails, emit a warning and continue
            self.logger.warning(f"Failed to log telemetry data: {e}")

    async def _create_async_iter(self, items: List[bytes]) -> AsyncGenerator[bytes, None]:
        """Create async iterator from list of bytes."""
        for item in items:
            yield item


def instrument_proxy_logging(model_specs: List[ModelSpec] | None) -> None:
    """Instrument LiteLLM proxy with telemetry logging middleware.

    This function should be called once during proxy startup to register
    telemetry middleware with FastAPI application.

    Args:
        model_specs: List of ModelSpec configurations for alias resolution
    """
    from litellm.proxy.proxy_server import app

    # Create alias lookup for model resolution
    alias_lookup = create_alias_lookup(model_specs or [])
    setattr(app.state, "litellm_telemetry_alias_lookup", alias_lookup)

    # Check if middleware is already registered
    if getattr(app.state, "_litellm_telemetry_installed", False):
        return

    # Configure logger regardless of middleware registration state
    logger = logging.getLogger("litellm_launcher.telemetry")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

    # Register middleware
    app.add_middleware(TelemetryMiddleware, alias_lookup=alias_lookup)
    setattr(app.state, "_litellm_telemetry_installed", True)
