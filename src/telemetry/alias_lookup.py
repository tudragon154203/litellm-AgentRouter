#!/usr/bin/env python3
"""
Model alias lookup functionality for telemetry module.
"""

from __future__ import annotations

from typing import Dict, List

from ..config.models import ModelSpec


def create_alias_lookup(model_specs: List[ModelSpec]) -> Dict[str, str]:
    """Create a lookup dictionary for model alias → upstream model resolution.

    Args:
        model_specs: List of ModelSpec configurations

    Returns:
        Dictionary mapping alias names to upstream model names (normalized with openai/ prefix)
    """
    lookup = {}
    for spec in model_specs:
        upstream_model = spec.upstream_model
        if not upstream_model.startswith("openai/"):
            upstream_model = f"openai/{upstream_model}"
        lookup[spec.alias] = upstream_model
    return lookup
