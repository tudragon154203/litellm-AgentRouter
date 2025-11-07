#!/usr/bin/env python3
"""
Configuration parsing functionality for LiteLLM proxy launcher.
"""

from __future__ import annotations

import os
from typing import List, Dict

from .models import ModelSpec, UpstreamSpec


def parse_upstream_registry() -> Dict[str, UpstreamSpec]:
    """Parse upstream definitions from environment variables.

    Scans for UPSTREAM_<NAME>_BASE_URL and UPSTREAM_<NAME>_API_KEY patterns.
    Upstream names are case-insensitive and stored as lowercase keys.

    Returns:
        Dictionary mapping lowercase upstream names to UpstreamSpec objects

    Raises:
        ValueError: If an upstream has only BASE_URL or only API_KEY
    """
    upstreams: Dict[str, Dict[str, str]] = {}

    # Scan environment for UPSTREAM_* variables
    for env_var, value in os.environ.items():
        if not env_var.startswith("UPSTREAM_"):
            continue

        # Parse variable name: UPSTREAM_<NAME>_BASE_URL or UPSTREAM_<NAME>_API_KEY
        parts = env_var.split("_", 2)  # Split into ['UPSTREAM', '<NAME>', 'BASE_URL' or 'API_KEY']
        if len(parts) < 3:
            continue

        upstream_name = parts[1].lower()  # Normalize to lowercase
        suffix = "_".join(parts[2:])  # Rejoin remaining parts (e.g., 'BASE_URL', 'API_KEY')

        if upstream_name not in upstreams:
            upstreams[upstream_name] = {}

        if suffix == "BASE_URL":
            upstreams[upstream_name]["base_url"] = value
        elif suffix == "API_KEY":
            upstreams[upstream_name]["api_key"] = value

    # Validate and create UpstreamSpec objects
    registry: Dict[str, UpstreamSpec] = {}
    for name, config in upstreams.items():
        base_url = config.get("base_url")
        api_key = config.get("api_key")

        if base_url and api_key:
            # Store the API key directly as api_key_env for backward compatibility with ModelSpec
            registry[name] = UpstreamSpec(name=name, base_url=base_url, api_key_env=api_key)
        elif base_url or api_key:
            # Incomplete upstream definition
            missing = "API_KEY" if not api_key else "BASE_URL"
            raise ValueError(
                f"Upstream '{name}' is incomplete. "
                f"Both UPSTREAM_{name.upper()}_BASE_URL and UPSTREAM_{name.upper()}_API_KEY must be defined. "
                f"Missing: UPSTREAM_{name.upper()}_{missing}"
            )

    return registry


def parse_model_spec(spec_str: str) -> ModelSpec:
    """Parse a model specification string into a ModelSpec object.

    Format: key=xxx,upstream=xxx[,alias=xxx][,base=xxx][,key_env=xxx][,reasoning=xxx]
    """
    parts = {}
    for part in spec_str.split(','):
        if '=' not in part:
            raise ValueError(f"Invalid model spec part: {part}")
        key, value = part.split('=', 1)
        parts[key.strip()] = value.strip()

    required_fields = ['key', 'upstream']
    missing = [field for field in required_fields if field not in parts]
    if missing:
        raise ValueError(f"Missing required fields in model spec: {missing}")

    # Alias is optional - derive from upstream if not provided
    alias = parts.get('alias')

    return ModelSpec(
        key=parts['key'],
        alias=alias,
        upstream_model=parts['upstream'],
        upstream_base=parts.get('base'),
        upstream_key_env=parts.get('key_env'),
        reasoning_effort=parts.get('reasoning'),
    )


def load_model_specs_from_env() -> List[ModelSpec]:
    """Load model specifications from environment variables using new multi-model schema."""
    proxy_model_keys = os.getenv("PROXY_MODEL_KEYS", "").strip()
    if not proxy_model_keys:
        raise ValueError(
            "PROXY_MODEL_KEYS is not set. "
            "Define at least one model using multi-model environment schema."
        )

    keys = [key.strip() for key in proxy_model_keys.split(',') if key.strip()]
    model_specs: List[ModelSpec] = []

    # Parse upstream registry
    upstream_registry = parse_upstream_registry()

    # Global defaults
    global_base = os.getenv("OPENAI_BASE_URL", "https://agentrouter.org/v1")
    global_key_env = "OPENAI_API_KEY"

    for key in keys:
        prefix = f"MODEL_{key.upper()}_"

        # Check for legacy alias variables and fail fast
        alias_env_var = f"{prefix}ALIAS"
        if os.getenv(alias_env_var):
            raise ValueError(
                f"Legacy environment variable '{alias_env_var}' detected. "
                f"Please remove it and use only MODEL_{key.upper()}_UPSTREAM_MODEL. "
                f"The alias will be automatically derived from the upstream model name."
            )

        upstream_model = os.getenv(f"{prefix}UPSTREAM_MODEL")
        reasoning_effort = os.getenv(f"{prefix}REASONING_EFFORT")

        if not upstream_model:
            raise ValueError(f"Missing environment variable: {prefix}UPSTREAM_MODEL")

        # Check for MODEL_<KEY>_UPSTREAM to reference named upstream
        upstream_name_raw = os.getenv(f"{prefix}UPSTREAM")
        upstream_name = None
        upstream_base = None
        upstream_key_env = None

        if upstream_name_raw:
            # Normalize upstream name to lowercase for lookup
            upstream_name = upstream_name_raw.lower()

            # Look up upstream in registry
            if upstream_name not in upstream_registry:
                available = ", ".join(sorted(upstream_registry.keys())) if upstream_registry else "none"
                raise ValueError(
                    f"Model '{key}' references unknown upstream '{upstream_name_raw}'. "
                    f"Available upstreams: {available}. "
                    f"Define UPSTREAM_{upstream_name_raw.upper()}_BASE_URL and "
                    f"UPSTREAM_{upstream_name_raw.upper()}_API_KEY_ENV."
                )

            # Resolve from upstream registry
            upstream_spec = upstream_registry[upstream_name]
            upstream_base = upstream_spec.base_url
            upstream_key_env = upstream_spec.api_key_env
        else:
            # Fall back to legacy per-model or global defaults
            upstream_base = os.getenv(f"{prefix}UPSTREAM_BASE") or global_base
            upstream_key_env = os.getenv(f"{prefix}UPSTREAM_KEY_ENV") or global_key_env

        # Create ModelSpec with alias=None to auto-derive from upstream_model
        model_specs.append(
            ModelSpec(
                key=key,
                alias=None,  # Let ModelSpec derive alias from upstream_model
                upstream_model=upstream_model,
                upstream_base=upstream_base,
                upstream_key_env=upstream_key_env,
                reasoning_effort=reasoning_effort,
                upstream_name=upstream_name,
            )
        )

    return model_specs


def validate_model_specs(model_specs: List[ModelSpec]) -> None:
    """Validate model specifications for conflicts.

    Checks for duplicate upstream model names across all models.

    Args:
        model_specs: List of ModelSpec objects to validate

    Raises:
        ValueError: If duplicate upstream model names are detected
    """
    upstream_model_map: Dict[str, List[str]] = {}

    # Collect all upstream_model values and their associated keys
    for spec in model_specs:
        upstream_model = spec.upstream_model
        if upstream_model not in upstream_model_map:
            upstream_model_map[upstream_model] = []
        upstream_model_map[upstream_model].append(spec.key)

    # Check for duplicates
    duplicates = {model: keys for model, keys in upstream_model_map.items() if len(keys) > 1}

    if duplicates:
        error_parts = []
        for upstream_model, keys in duplicates.items():
            keys_str = ", ".join(keys)
            error_parts.append(f"'{upstream_model}' found in models: {keys_str}")

        raise ValueError(
            f"Duplicate upstream model name(s) detected. "
            f"Each model must have a unique upstream model name. "
            f"Conflicts: {'; '.join(error_parts)}"
        )


def load_model_specs_from_cli(model_spec_args: List[str] | None) -> List[ModelSpec]:
    """Load model specifications from CLI --model-spec arguments."""
    if not model_spec_args:
        return []

    return [parse_model_spec(spec_str) for spec_str in model_spec_args]


def prepare_config(args) -> tuple[str, bool]:
    """Prepare configuration from args, returning (config_text, is_generated).

    Args:
        args: Parsed CLI arguments with attributes like config, model_specs, etc.

    Returns:
        Tuple of (config_text, is_generated) where:
        - config_text: YAML configuration string
        - is_generated: True if config was generated from specs/env, False if from file
    """
    from pathlib import Path
    import os
    import sys
    from .rendering import render_config

    # If config file is provided, read and return it
    if getattr(args, 'config', None):
        config_path = Path(args.config)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {args.config}")

        return config_path, False

    # Otherwise generate config from model specs or environment
    model_specs = getattr(args, 'model_specs', None)

    if not model_specs:
        # Try loading from environment
        try:
            model_specs = load_model_specs_from_env()
            # Store model specs back into args for consistency
            setattr(args, 'model_specs', model_specs)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate model specifications
    try:
        validate_model_specs(model_specs)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Check for missing environment variables in model specs
    for spec in model_specs:
        if spec.upstream_key_env and not os.getenv(spec.upstream_key_env):
            print(
                f"WARNING: Environment variable '{spec.upstream_key_env}' "
                f"for model '{spec.alias}' is not set",
                file=sys.stderr
            )

    # Get configuration parameters from args with defaults
    global_upstream_base = getattr(args, 'upstream_base', None) or "https://agentrouter.org/v1"
    global_upstream_key_env = getattr(args, 'upstream_key_env', None) or "OPENAI_API_KEY"
    master_key = None if getattr(args, 'no_master_key', False) else getattr(args, 'master_key', "sk-local-master")
    drop_params = getattr(args, 'drop_params', True)
    streaming = getattr(args, 'streaming', True)

    # Generate configuration
    config_text = render_config(
        model_specs=model_specs,
        global_upstream_base=global_upstream_base,
        global_upstream_key_env=global_upstream_key_env,
        master_key=master_key,
        drop_params=drop_params,
        streaming=streaming,
    )

    return config_text, True
