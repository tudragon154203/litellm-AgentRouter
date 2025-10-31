#!/usr/bin/env python3
"""
Main entry point for LiteLLM proxy launcher.
"""

from __future__ import annotations

import sys
from typing import NoReturn

from .cli import parse_args
from .config import prepare_config, create_temp_config_if_needed
from .proxy import start_proxy
from .utils import attach_signal_handlers, load_dotenv_files, validate_prereqs


def main(argv: list[str] | None = None) -> NoReturn:
    """Main entry point for the LiteLLM proxy launcher."""
    load_dotenv_files()
    validate_prereqs()
    args = parse_args(argv)
    attach_signal_handlers()

    config_data, is_generated = prepare_config(args)

    with create_temp_config_if_needed(config_data, is_generated) as config_path:
        if is_generated:
            print(
                f"Starting LiteLLM proxy on {args.host}:{args.port} "
                f"with generated config (alias={args.alias})."
            )
        else:
            print(
                f"Starting LiteLLM proxy on {args.host}:{args.port} "
                f"using config file {config_path}."
            )
        start_proxy(args, config_path)

    # This should never be reached, but included for completeness
    sys.exit(0)


if __name__ == "__main__":
    main()
