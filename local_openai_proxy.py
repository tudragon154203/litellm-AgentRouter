#!/usr/bin/env python3
"""
LiteLLM local proxy launcher.

This script replaces the old minimal LiteLLM client example and spins up a
LiteLLM proxy (OpenAI-compatible gateway) configured from environment
variables or CLI flags. Other services can then target the local proxy instead
of calling upstream providers directly.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Tuple


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_dotenv_files() -> None:
    """Load key-value pairs from .env files into the current environment."""
    def load_file(path: Path) -> None:
        if not path.is_file():
            return
        try:
            for raw_line in path.read_text().splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception as exc:
            print(f"WARNING: failed to load {path}: {exc}", file=sys.stderr)

    script_dir = Path(__file__).resolve().parent
    cwd = Path.cwd()
    seen: set[Path] = set()
    for candidate in (script_dir / ".env", cwd / ".env"):
        if candidate not in seen:
            seen.add(candidate)
            load_file(candidate)


def _quote(value: str) -> str:
    """Return a JSON-escaped string that is also valid YAML."""
    return json.dumps(value)


def render_config(
    *,
    alias: str,
    upstream_model: str,
    upstream_base: str,
    upstream_key_env: str | None,
    master_key: str | None,
    drop_params: bool,
) -> str:
    """Render a minimal LiteLLM proxy config."""
    lines = [
        "model_list:",
        f"  - model_name: {_quote(alias)}",
        "    litellm_params:",
        f"      model: {_quote(upstream_model)}",
        f"      api_base: {_quote(upstream_base)}",
    ]
    if upstream_key_env:
        lines.append(f"      api_key: {_quote(f'os.environ/{upstream_key_env}')}")
    else:
        lines.append("      api_key: null")

    lines.append("")

    lines.append("litellm_settings:")
    lines.append(f"  drop_params: {'true' if drop_params else 'false'}")

    if master_key:
        lines.append("")
        lines.append("general_settings:")
        lines.append(f"  master_key: {_quote(master_key)}")

    return "\n".join(lines) + "\n"


@contextmanager
def _temporary_config(config_text: str) -> Iterator[Path]:
    """Persist a temporary config file for the lifetime of the context."""
    config_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="litellm-config-", delete=False
    )
    try:
        with config_file as handle:
            handle.write(config_text)
            handle.flush()
            path = Path(handle.name)
        yield path
    finally:
        try:
            Path(config_file.name).unlink(missing_ok=True)
        except Exception:
            pass


def _validate_prereqs() -> None:
    try:
        import litellm  # noqa: F401
        import litellm.proxy.proxy_cli  # noqa: F401
    except ImportError as exc:  # pragma: no cover - import error reported to user
        print(
            "ERROR: LiteLLM proxy dependencies are missing. "
            "Install them with `pip install 'litellm[proxy]'`.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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
        default=os.getenv("LITELLM_MODEL_ALIAS", "local-gpt"),
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
        default=os.getenv("UPSTREAM_API_KEY_ENV", "OPENAI_API_KEY"),
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
        default=_env_bool("LITELLM_DEBUG"),
        help="Enable LiteLLM debug logging.",
    )
    parser.add_argument(
        "--detailed-debug",
        action="store_true",
        default=_env_bool("LITELLM_DETAILED_DEBUG"),
        help="Enable verbose LiteLLM proxy debug logging.",
    )
    parser.add_argument(
        "--no-master-key",
        action="store_true",
        help="Disable setting a proxy master key in the generated config.",
    )
    drop_default = _env_bool("LITELLM_DROP_PARAMS", True)
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


def _prepare_config(args: argparse.Namespace) -> Tuple[Path | str, bool]:
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
    )

    if args.print_config:
        print(config_text, end="")
        raise SystemExit(0)

    return config_text, True


def _attach_signal_handlers() -> None:
    def handle_signal(signum, frame):  # pragma: no cover - runtime behaviour
        signame = signal.Signals(signum).name
        print(f"\nReceived {signame}, shutting down LiteLLM proxy...", file=sys.stderr)
        raise SystemExit(0)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)


def start_proxy(args: argparse.Namespace, config_path: Path) -> None:
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


def main(argv: list[str] | None = None) -> None:
    _load_dotenv_files()
    _validate_prereqs()
    args = parse_args(argv)
    _attach_signal_handlers()

    config_data, is_generated = _prepare_config(args)

    if is_generated:
        config_text = str(config_data)
        with _temporary_config(config_text) as temp_path:
            print(
                f"Starting LiteLLM proxy on {args.host}:{args.port} "
                f"with generated config (alias={args.alias})."
            )
            start_proxy(args, temp_path)
    else:
        config_path = Path(config_data)
        print(
            f"Starting LiteLLM proxy on {args.host}:{args.port} "
            f"using config file {config_path}."
        )
        start_proxy(args, config_path)


if __name__ == "__main__":
    main()
