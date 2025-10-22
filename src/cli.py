#!/usr/bin/env python3
"""
Command-line interface for LiteLLM proxy launcher.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .utils import env_bool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the LiteLLM proxy."""
    parser = argparse.ArgumentParser(
        description=(
            "Start a LiteLLM proxy that exposes a local OpenAI-compatible API. "
            "By default a minimal config is generated using upstream environment "
            "variables; pass --config to supply your own config.yaml."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=os.getenv("LITELLM_CONFIG"),
        help="Path to an existing LiteLLM config.yaml.",
    )
    parser.add_argument(
        "--alias",
        default=os.getenv("LITELLM_MODEL_ALIAS", "gpt-5"),
        help="Public model name to expose from the proxy.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o"),
        help="Upstream provider model identifier.",
    )
    parser.add_argument(
        "--upstream-base",
        dest="upstream_base",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        help="Base URL for the upstream OpenAI-compatible endpoint.",
    )
    parser.add_argument(
        "--upstream-key-env",
        dest="upstream_key_env",
        default="OPENAI_API_KEY",
        help=(
            "Environment variable that stores the upstream API key. "
            "Set to blank to skip setting an API key in the generated config."
        ),
    )
    parser.add_argument(
        "--master-key",
        dest="master_key",
        default=os.getenv("LITELLM_MASTER_KEY", "sk-local-master"),
        help="Optional master key enforced by the proxy (Authorization bearer token).",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("LITELLM_HOST", "0.0.0.0"),
        help="Host interface for the proxy.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("LITELLM_PORT", "4000")),
        help="Port for the proxy.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("LITELLM_WORKERS", "1")),
        help="Number of worker processes to run.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=env_bool("LITELLM_DEBUG"),
        help="Enable LiteLLM debug logging.",
    )
    parser.add_argument(
        "--detailed-debug",
        action="store_true",
        default=env_bool("LITELLM_DETAILED_DEBUG"),
        help="Enable verbose LiteLLM proxy debug logging.",
    )
    parser.add_argument(
        "--no-master-key",
        action="store_true",
        help="Disable setting a proxy master key in the generated config.",
    )
    drop_default = env_bool("LITELLM_DROP_PARAMS", True)
    parser.add_argument(
        "--drop-params",
        dest="drop_params",
        action="store_true",
        default=drop_default,
        help="Enable litellm.drop_params in the generated config.",
    )
    parser.add_argument(
        "--no-drop-params",
        dest="drop_params",
        action="store_false",
        help="Disable litellm.drop_params in the generated config.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print the generated config and exit (useful for inspection).",
    )
    return parser.parse_args(argv)