#!/usr/bin/env python3
"""
Main entry point for LiteLLM proxy launcher.
"""

from __future__ import annotations

import sys
from typing import NoReturn
from pathlib import Path

from .cli import parse_args
from .config.parsing import prepare_config
from .utils import create_temp_config_if_needed
from .proxy import start_proxy
from .utils import attach_signal_handlers, load_dotenv_files, validate_prereqs


def get_startup_message(args) -> str:
    """Generate startup message with model information."""
    host_port = f"{args.host}:{args.port}"
    model_specs = getattr(args, "model_specs", None) or []

    if args.config:
        # Using config file
        return f"Starting LiteLLM proxy on {host_port} using config file {args.config}"

    if model_specs:
        alias_info = ", ".join(f"{spec.alias} ({spec.upstream_model})" for spec in model_specs)
        return f"Starting LiteLLM proxy on {host_port} with {len(model_specs)} model(s): {alias_info}"

    # Should not happen: prepare_config enforces presence of model specs.
    return (
        f"Starting LiteLLM proxy on {host_port} with generated config "
        "(no model specifications found)"
    )


def main(argv: list[str] | None = None) -> NoReturn:
    """Main entry point for the LiteLLM proxy launcher."""
    load_dotenv_files()
    validate_prereqs()
    args = parse_args(argv)
    attach_signal_handlers()

    config_data, is_generated = prepare_config(args)

    # Handle --print-config flag: print config and exit
    if getattr(args, 'print_config', False) is True:
        if is_generated:
            print(config_data)
        else:
            config_path = Path(config_data)
            print(config_path.read_text(encoding="utf-8"))
        sys.exit(0)
        return

    with create_temp_config_if_needed(config_data, is_generated) as config_path:
        print(get_startup_message(args))
        start_proxy(args, config_path)

    # This should never be reached, but included for completeness
    sys.exit(0)


if __name__ == "__main__":
    main()
