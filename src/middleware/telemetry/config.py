#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

from fastapi import Request


class TelemetryToggle(Protocol):
    def enabled(self, request: Request) -> bool: ...


class AliasResolver(Protocol):
    def __call__(self, alias: str) -> str: ...


class ReasoningPolicy(Protocol):
    def apply(self, request: Request): ...


class TelemetrySink(Protocol):
    def emit(self, event: dict) -> None: ...


@dataclass(frozen=True)
class TelemetryConfig:
    toggle: TelemetryToggle
    alias_resolver: AliasResolver | Callable[[str], str]
    sinks: Sequence[TelemetrySink]
    reasoning_policy: ReasoningPolicy
