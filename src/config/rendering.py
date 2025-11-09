#!/usr/bin/env python3
"""
Configuration rendering functionality for LiteLLM proxy launcher.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List

from ..utils import build_user_agent, quote
from . import models
from .models import ModelSpec


def render_model_entry(model_spec: ModelSpec, global_defaults: Dict[str, Any]) -> List[str]:
    """Render a single model entry for LiteLLM config."""
    # Use defaults from model_spec, falling back to global defaults
    upstream_base = model_spec.upstream_base or global_defaults.get("upstream_base", "https://agentrouter.org/v1")

    # Convert model to openai/ format if it's not already prefixed
    upstream_model = model_spec.upstream_model
    if not upstream_model.startswith("openai/"):
        upstream_model = f"openai/{upstream_model}"

    lines = [
        f"  - model_name: {quote(model_spec.alias)}",
        "    litellm_params:",
        f"      model: {quote(upstream_model)}",
        f"      api_base: {quote(upstream_base)}",
        f"      custom_llm_provider: {quote('openai')}",
        "      headers:",
        f"        \"User-Agent\": {quote(build_user_agent())}",
        f"        \"Content-Type\": {quote('application/json')}",
    ]

    # Check model capabilities and add reasoning_effort if supported
    capabilities = models.get_model_capabilities(model_spec.upstream_model)
    reasoning_effort = model_spec.reasoning_effort

    if reasoning_effort and reasoning_effort != "none":
        if capabilities.get("supports_reasoning", True):
            lines.append(f"      reasoning_effort: {quote(reasoning_effort)}")
        else:
            # Model doesn't support reasoning, but user explicitly set it
            # This could be a warning in future
            print(
                f"WARNING: Model {model_spec.upstream_model} does not support reasoning_effort, "
                f"ignoring reasoning_effort={reasoning_effort}",
                file=sys.stderr,
            )

    return lines


def render_config(
    *,
    model_specs: List[ModelSpec],
    global_upstream_base: str,
    master_key: str | None,
    drop_params: bool,
    streaming: bool,
) -> str:
    """Render a LiteLLM proxy config supporting one or more models."""
    if not model_specs:
        raise ValueError("No model specifications provided")

    lines = ["model_list:"]
    global_defaults = {
        "upstream_base": global_upstream_base,
    }

    for model_spec in model_specs:
        lines.extend(render_model_entry(model_spec, global_defaults))

    lines.append("")
    lines.append("litellm_settings:")
    lines.append(f"  drop_params: {'true' if drop_params else 'false'}")
    lines.append("  set_verbose: false")

    if master_key:
        lines.append("")
        lines.append("general_settings:")
        lines.append(f"  master_key: {quote(master_key)}")

    return "\n".join(lines) + "\n"
