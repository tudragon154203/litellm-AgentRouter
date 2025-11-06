#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UsageTokens:
    """Token counts extracted from responses."""
    total: int | None = None
    prompt: int | None = None
    completion: int | None = None
    reasoning: int | None = None

    def __iter__(self):
        return iter(self.__dict__.items())

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()


@dataclass(frozen=True)
class RequestReceived:
    """Event emitted when a request is received by telemetry."""
    timestamp: str
    method: str
    path: str
    model_alias: str | None = None
    client_request_id: str | None = None
    remote_addr: str | None = None
    reasoning_metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ResponseCompleted:
    """Event emitted when a response completes successfully."""
    timestamp: str
    duration_s: float
    status_code: int
    upstream_model: str
    usage: UsageTokens | None = None
    streaming: bool = False
    parse_error: bool = False
    missing_usage: bool = False
    client_request_id: str | None = None
    remote_addr: str | None = None


@dataclass(frozen=True)
class ErrorRaised:
    """Event emitted when request processing raises an exception."""
    timestamp: str
    duration_s: float
    status_code: int
    error_type: str
    error_message: str
    streaming: bool = False
    client_request_id: str | None = None
    remote_addr: str | None = None
