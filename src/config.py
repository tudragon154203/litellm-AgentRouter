#!/usr/bin/env python3
"""
Configuration generation and handling for LiteLLM proxy launcher.
"""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .utils import quote, temporary_config


@dataclass
class ModelSpec:
    """Configuration for a single model in the proxy."""
    key: str  # Logical key identifier
    alias: str  # Public model name exposed by proxy
    upstream_model: str  # Upstream provider model ID
    upstream_base: str | None = None  # Base URL (defaults to global)
    upstream_key_env: str | None = None  # API key env var (defaults to global)
    reasoning_effort: str | None = None  # Reasoning effort level

    def __post_init__(self) -> None:
        """Validate the model spec after creation."""
        if not self.key:
            raise ValueError("Model key cannot be empty")
        if not self.alias:
            raise ValueError("Model alias cannot be empty")
        if not self.upstream_model:
            raise ValueError("Upstream model cannot be empty")


# Model capability mapping
MODEL_CAPS: Dict[str, Dict[str, Any]] = {
    "deepseek-v3.2": {"supports_reasoning": True},
    "gpt-5": {"supports_reasoning": True},
    # Add more models as needed
}


def get_model_capabilities(upstream_model: str) -> Dict[str, Any]:
    """Get capabilities for a model, defaulting to unknown model capabilities."""
    return MODEL_CAPS.get(upstream_model, {"supports_reasoning": True})  # Default to supporting reasoning


def parse_model_spec(spec_str: str) -> ModelSpec:
    """Parse a model specification string into a ModelSpec object.

    Format: key=xxx,alias=xxx,upstream=xxx[,base=xxx][,key_env=xxx][,reasoning=xxx]
    """
    parts = {}
    for part in spec_str.split(','):
        if '=' not in part:
            raise ValueError(f"Invalid model spec part: {part}")
        key, value = part.split('=', 1)
        parts[key.strip()] = value.strip()

    required_fields = ['key', 'alias', 'upstream']
    missing = [field for field in required_fields if field not in parts]
    if missing:
        raise ValueError(f"Missing required fields in model spec: {missing}")

    return ModelSpec(
        key=parts['key'],
        alias=parts['alias'],
        upstream_model=parts['upstream'],
        upstream_base=parts.get('base'),
        upstream_key_env=parts.get('key_env'),
        reasoning_effort=parts.get('reasoning'),
    )


def load_model_specs_from_env() -> List[ModelSpec]:
    """Load model specifications from environment variables using the new multi-model schema."""
    proxy_model_keys = os.getenv("PROXY_MODEL_KEYS", "").strip()
    if not proxy_model_keys:
        raise ValueError(
            "PROXY_MODEL_KEYS is not set. "
            "Define at least one model using the multi-model environment schema."
        )

    keys = [key.strip() for key in proxy_model_keys.split(',') if key.strip()]
    model_specs: List[ModelSpec] = []

    # Global defaults
    global_base = os.getenv("OPENAI_API_BASE", "https://agentrouter.org/v1")
    global_key_env = "OPENAI_API_KEY"

    for key in keys:
        prefix = f"MODEL_{key.upper()}_"

        alias = os.getenv(f"{prefix}ALIAS")
        upstream_model = os.getenv(f"{prefix}UPSTREAM_MODEL")
        upstream_base = os.getenv(f"{prefix}UPSTREAM_BASE") or global_base
        upstream_key_env = os.getenv(f"{prefix}UPSTREAM_KEY_ENV") or global_key_env
        reasoning_effort = os.getenv(f"{prefix}REASONING_EFFORT")

        if not alias:
            raise ValueError(f"Missing environment variable: {prefix}ALIAS")
        if not upstream_model:
            raise ValueError(f"Missing environment variable: {prefix}UPSTREAM_MODEL")

        model_specs.append(
            ModelSpec(
                key=key,
                alias=alias,
                upstream_model=upstream_model,
                upstream_base=upstream_base,
                upstream_key_env=upstream_key_env,
                reasoning_effort=reasoning_effort,
            )
        )

    return model_specs


def load_model_specs_from_cli(model_spec_args: List[str] | None) -> List[ModelSpec]:
    """Load model specifications from CLI --model-spec arguments."""
    if not model_spec_args:
        return []

    return [parse_model_spec(spec_str) for spec_str in model_spec_args]


def render_model_entry(model_spec: ModelSpec, global_defaults: Dict[str, Any]) -> List[str]:
    """Render a single model entry for the LiteLLM config."""
    # Use defaults from model_spec, falling back to global defaults
    upstream_base = model_spec.upstream_base or global_defaults.get("upstream_base", "https://agentrouter.org/v1")
    upstream_key_env = model_spec.upstream_key_env or global_defaults.get("upstream_key_env")

    # Convert model to openai/ format if it's not already prefixed
    upstream_model = model_spec.upstream_model
    if not upstream_model.startswith("openai/"):
        upstream_model = f"openai/{upstream_model}"

    lines = [
        f"  - model_name: {quote(model_spec.alias)}",
        "    litellm_params:",
        f"      model: {quote(upstream_model)}",
        f"      api_base: {quote(upstream_base)}",
    ]

    if upstream_key_env:
        lines.append(f"      api_key: {quote(f'os.environ/{upstream_key_env}')}")
    else:
        lines.append("      api_key: null")

    # Check model capabilities and add reasoning_effort if supported
    capabilities = get_model_capabilities(model_spec.upstream_model)
    reasoning_effort = model_spec.reasoning_effort

    if reasoning_effort and reasoning_effort != "none":
        if capabilities.get("supports_reasoning", True):
            lines.append(f"      reasoning_effort: {quote(reasoning_effort)}")
        else:
            # Model doesn't support reasoning, but user explicitly set it
            # This could be a warning in the future
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
    global_upstream_key_env: str | None,
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
        "upstream_key_env": global_upstream_key_env,
    }

    for model_spec in model_specs:
        lines.extend(render_model_entry(model_spec, global_defaults))

    lines.append("")
    lines.append("litellm_settings:")
    lines.append(f"  drop_params: {'true' if drop_params else 'false'}")
    lines.append(f"  set_verbose: {'true' if streaming else 'false'}")

    if master_key:
        lines.append("")
        lines.append("general_settings:")
        lines.append(f"  master_key: {quote(master_key)}")

    return "\n".join(lines) + "\n"


def prepare_config(args: argparse.Namespace) -> Tuple[Path | str, bool]:
    """
    Prepare the configuration for the LiteLLM proxy.

    Returns:
        Tuple of (config_path_or_text, is_generated)
        - If is_generated is True, the first element is the config text
        - If is_generated is False, the first element is the Path to existing config
    """
    if args.config:
        config_path = Path(args.config)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return config_path, False

    model_specs = getattr(args, "model_specs", None) or []
    if not model_specs:
        try:
            model_specs = load_model_specs_from_env()
        except ValueError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            raise SystemExit(1) from error

    for spec in model_specs:
        env_name = spec.upstream_key_env
        if env_name and env_name not in os.environ:
            print(
                f"WARNING: Environment variable '{env_name}' "
                f"for model '{spec.alias}' is not set. "
                "Upstream calls may fail authentication.",
                file=sys.stderr,
            )

    master_key = None if args.no_master_key else args.master_key
    global_upstream_base = getattr(args, "upstream_base", None) or os.getenv(
        "OPENAI_API_BASE",
        "https://agentrouter.org/v1",
    )
    global_upstream_key_env = getattr(args, "upstream_key_env", None) or "OPENAI_API_KEY"

    config_text = render_config(
        model_specs=model_specs,
        global_upstream_base=global_upstream_base,
        global_upstream_key_env=global_upstream_key_env,
        master_key=master_key,
        drop_params=args.drop_params,
        streaming=args.streaming,
    )

    setattr(args, "model_specs", model_specs)

    if args.print_config:
        print(config_text, end="")
        raise SystemExit(0)

    return config_text, True


@contextmanager
def create_temp_config_if_needed(config_data: Path | str, is_generated: bool):
    """
    Create a temporary config file if needed.

    Args:
        config_data: Either a Path to existing config or config text
        is_generated: Whether the config_data is generated text

    Yields:
        Path to the config file to use
    """
    if is_generated:
        config_text = str(config_data)
        with temporary_config(config_text) as temp_path:
            yield temp_path
    else:
        yield config_data
