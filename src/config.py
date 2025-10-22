#!/usr/bin/env python3
"""
Configuration generation and handling for LiteLLM proxy launcher.
"""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Tuple

from .utils import quote, temporary_config


def render_config(
    *,
    alias: str,
    upstream_model: str,
    upstream_base: str,
    upstream_key_env: str | None,
    master_key: str | None,
    drop_params: bool,
    streaming: bool,
) -> str:
    """Render a minimal LiteLLM proxy config."""
    # Convert model to openai/ format if it's not already prefixed
    if not upstream_model.startswith("openai/"):
        upstream_model = f"openai/{upstream_model}"

    lines = [
        "model_list:",
        f"  - model_name: {quote(alias)}",
        "    litellm_params:",
        f"      model: {quote(upstream_model)}",
        f"      api_base: {quote(upstream_base)}",
    ]
    if upstream_key_env:
        lines.append(f"      api_key: {quote(f'os.environ/{upstream_key_env}')}")
    else:
        lines.append("      api_key: null")

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

    upstream_key_env = args.upstream_key_env or None
    if upstream_key_env and upstream_key_env not in os.environ:
        print(
            f"WARNING: Environment variable '{upstream_key_env}' is not set. "
            "Upstream calls may fail authentication.",
            file=sys.stderr,
        )
    master_key = None if args.no_master_key else args.master_key
    config_text = render_config(
        alias=args.alias,
        upstream_model=args.model,
        upstream_base=args.upstream_base,
        upstream_key_env=upstream_key_env,
        master_key=master_key,
        drop_params=args.drop_params,
        streaming=args.streaming,
    )

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