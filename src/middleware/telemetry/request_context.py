#!/usr/bin/env python3
from __future__ import annotations


from fastapi import Request

from .config import ReasoningPolicy


class NoOpReasoningPolicy:
    """No-op reasoning policy that leaves requests unchanged."""

    def apply(self, request: Request) -> tuple[Request, dict]:
        return request, {}


def apply_reasoning_policy(policy: ReasoningPolicy, request: Request) -> tuple[Request, dict]:
    """Apply reasoning policy safely with fallback to no-op."""
    try:
        return policy.apply(request)
    except Exception:
        # If policy fails, fall back to no-op to avoid breaking request flow
        return NoOpReasoningPolicy().apply(request)
