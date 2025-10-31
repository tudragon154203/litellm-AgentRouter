#!/usr/bin/env python3
"""
Proxy startup and management for LiteLLM proxy launcher.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def start_proxy(args: argparse.Namespace, config_path: Path) -> None:
    """Start the LiteLLM proxy with the given configuration."""
    from litellm.proxy.proxy_cli import run_server

    cli_args = [
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--num_workers",
        str(args.workers),
        "--config",
        str(config_path),
    ]

    if args.debug:
        cli_args.append("--debug")
    if args.detailed_debug:
        cli_args.append("--detailed_debug")

    try:
        run_server.main(cli_args, standalone_mode=False)
    except SystemExit as exc:  # pragma: no cover - click invocation
        if exc.code not in (0, None):
            raise
