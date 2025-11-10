#!/usr/bin/env python3
"""
Docker entrypoint module for LiteLLM proxy launcher.

This module replaces the bash entrypoint.sh script with Python implementation,
providing better testability and maintainability.
"""

from __future__ import annotations

import os
import re
import sys
from typing import NoReturn

from .config import runtime_config
from .parsing import load_model_specs_from_env
from .rendering import render_config


def validate_environment() -> None:
    """Validate required environment variables.

    Raises:
        SystemExit: If PROXY_MODEL_KEYS is missing or empty
    """
    runtime_config.ensure_loaded()

    proxy_keys = runtime_config.get_str("PROXY_MODEL_KEYS", "").strip()
    if not proxy_keys:
        print("ERROR: PROXY_MODEL_KEYS must be set (comma-separated logical keys).", file=sys.stderr)
        sys.exit(1)


def mask_sensitive_value(value: str, visible_chars: int = 4, visible_suffix: int = 2) -> str:
    """Partially mask a sensitive value for logging.

    Args:
        value: The sensitive value to mask
        visible_chars: Number of characters to show at start
        visible_suffix: Number of characters to show at end

    Returns:
        Partially masked string (e.g., "sk-1***ef")
    """
    if len(value) <= visible_chars + visible_suffix:
        return value[:visible_chars] + "***"
    return value[:visible_chars] + "***" + value[-visible_suffix:]


def mask_config_output(config_text: str) -> str:
    """Mask sensitive values in YAML configuration for logging.

    Args:
        config_text: The YAML configuration text

    Returns:
        Configuration with api_key and master_key values partially masked
    """
    # Mask api_key values
    config_text = re.sub(
        r'(api_key:\s*["\']?)([^\s"\']+)(["\']?)',
        lambda m: m.group(1) + mask_sensitive_value(m.group(2)) + m.group(3),
        config_text
    )
    # Mask master_key values
    config_text = re.sub(
        r'(master_key:\s*["\']?)([^\s"\']+)(["\']?)',
        lambda m: m.group(1) + mask_sensitive_value(m.group(2)) + m.group(3),
        config_text
    )
    return config_text


def write_config_file(config_text: str, path: str) -> None:
    """Write configuration to file.

    Args:
        config_text: The YAML configuration text
        path: File path to write to
    """
    with open(path, 'w') as f:
        f.write(config_text)


def main() -> NoReturn:
    """Main entrypoint function for Docker container startup.

    Flow:
        1. Print startup message
        2. Validate environment variables
        3. Load model specs from environment
        4. Generate YAML configuration
        5. Write configuration to file
        6. Print masked configuration
        7. Execute src.main with generated config
    """
    print("Starting LiteLLM proxy launcher (Python entrypoint)...")

    # Validate environment
    validate_environment()

    # Load model specs from environment
    try:
        model_specs = load_model_specs_from_env()
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate configuration
    runtime_config.ensure_loaded()
    global_upstream_base = runtime_config.get_str("OPENAI_BASE_URL", "https://agentrouter.org/v1")
    api_key = runtime_config.get_str("OPENAI_API_KEY")
    master_key = runtime_config.get_str("LITELLM_MASTER_KEY", "sk-local-master")

    try:
        config_text = render_config(
            model_specs=model_specs,
            global_upstream_base=global_upstream_base,
            master_key=master_key,
            drop_params=True,
            streaming=True,
            api_key=api_key,
        )
    except Exception as e:
        print(f"ERROR: Failed to generate configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Write configuration to file
    config_path = "/app/generated-config.yaml"
    try:
        write_config_file(config_text, config_path)
    except Exception as e:
        print(f"ERROR: Failed to write configuration file: {e}", file=sys.stderr)
        sys.exit(1)

    # Print masked configuration
    print("\nGenerated configuration:")
    print("=" * 80)
    print(mask_config_output(config_text))
    print("=" * 80)

    # Get host and port configuration
    host = runtime_config.get_str("LITELLM_HOST", "0.0.0.0")
    container_port = 4000
    host_port = runtime_config.get_str("PORT", "4000")

    print(f"\nContainer listening on port {container_port}; host publishes {host_port} -> {container_port}")
    print(f"Starting LiteLLM proxy on {host}:{container_port}...\n")

    # Execute src.main with generated config
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "src.main",
            "--config",
            config_path,
            "--host",
            host,
            "--port",
            str(container_port),
        ]
    )


if __name__ == "__main__":  # pragma: no cover
    main()
