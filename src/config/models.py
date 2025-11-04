#!/usr/bin/env python3
"""
Configuration models for LiteLLM proxy launcher.
"""

from __future__ import annotations

from typing import Dict, Any, Optional


def derive_alias(upstream_model: str) -> str:
    """Derive public alias from upstream model identifier.

    Args:
        upstream_model: The upstream model identifier (e.g., 'openai/gpt-5', 'deepseek-v3.2')

    Returns:
        Derived alias string (e.g., 'gpt-5', 'deepseek-v3.2')
    """
    # Strip known provider prefixes
    known_prefixes = ['openai/', 'anthropic/', 'google/', 'azure/']

    for prefix in known_prefixes:
        if upstream_model.startswith(prefix):
            return upstream_model[len(prefix):]

    # Return upstream model unchanged when no known prefix exists
    return upstream_model


class ModelSpec:
    """Configuration for a single model in the proxy."""

    def __init__(
        self,
        key: str,
        upstream_model: str,
        alias: Optional[str] = None,
        upstream_base: Optional[str] = None,
        upstream_key_env: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
    ):
        """Initialize ModelSpec.

        Args:
            key: Logical key identifier
            alias: Public model name exposed by proxy (auto-derived if not provided)
            upstream_model: Upstream provider model ID
            upstream_base: Base URL (defaults to global)
            upstream_key_env: API key env var (defaults to global)
            reasoning_effort: Reasoning effort level
        """
        self.key = key
        self.alias = alias or derive_alias(upstream_model)
        self.upstream_model = upstream_model
        self.upstream_base = upstream_base
        self.upstream_key_env = upstream_key_env
        self.reasoning_effort = reasoning_effort
        self._validate()

    def _validate(self) -> None:
        """Validate model spec parameters."""
        if not self.key:
            raise ValueError("Model key cannot be empty")
        if not self.upstream_model:
            raise ValueError("Upstream model cannot be empty")

    def __post_init__(self) -> None:
        """Legacy compatibility - validation now done in __init__."""
        pass


# Model capability mapping
MODEL_CAPS: Dict[str, Dict[str, Any]] = {
    "deepseek-v3.2": {"supports_reasoning": True},
    "gpt-5": {"supports_reasoning": True},
    "glm-4.6": {"supports_reasoning": False},
    "grok-code-fast-1": {"supports_reasoning": True},
    # Add more models as needed
}


def get_model_capabilities(upstream_model: str) -> Dict[str, Any]:
    """Get capabilities for a model, defaulting to unknown model capabilities."""
    return MODEL_CAPS.get(upstream_model, {"supports_reasoning": True})  # Default to not supporting reasoning
