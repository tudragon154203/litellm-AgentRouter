#!/usr/bin/env python3
"""
Centralized configuration object for LiteLLM proxy launcher.

This module provides a unified interface for loading and accessing
configuration from .env files and environment variables.
"""

from __future__ import annotations

import os
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterator


class MissingSettingError(Exception):
    """Raised when a required configuration setting is missing."""

    def __init__(self, key: str):
        super().__init__(f"Required configuration setting '{key}' is missing")
        self.key = key


class RuntimeConfig:
    """Centralized configuration object with .env loading and typed accessors."""

    def __init__(self, overrides: dict[str, str] | None = None):
        """Initialize configuration object.

        Args:
            overrides: Optional dictionary of override values for testing.
        """
        self._loaded = False
        self._load_lock = threading.Lock()
        self._overrides = MappingProxyType(overrides) if overrides else None

    def ensure_loaded(self) -> None:
        """Load .env files into environment if not already loaded.

        This method is idempotent - calling it multiple times will only
        load .env files once. Respects SKIP_DOTENV environment variable.
        """
        if self._loaded:
            return

        with self._load_lock:
            # Double-check after acquiring lock
            if self._loaded:
                return

            if os.getenv("SKIP_DOTENV"):
                self._loaded = True
                return

            self._load_dotenv_files()
            self._loaded = True

    def _load_dotenv_files(self) -> None:
        """Internal method to load .env files into environment."""

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

        # Search for .env in script directory and current working directory
        script_dir = Path(__file__).resolve().parent.parent
        cwd = Path.cwd()
        seen: set[Path] = set()

        for candidate in (script_dir / ".env", cwd / ".env"):
            if candidate not in seen:
                seen.add(candidate)
                load_file(candidate)

    def _get_value(self, key: str) -> str | None:
        """Get value from overrides or environment."""
        if self._overrides and key in self._overrides:
            return self._overrides[key]
        return os.getenv(key)

    def get_str(self, key: str, default: str | None = None) -> str | None:
        """Get string configuration value.

        Args:
            key: Environment variable name.
            default: Default value if key is not present.

        Returns:
            String value or default.
        """
        value = self._get_value(key)
        return value if value is not None else default

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Get integer configuration value.

        Args:
            key: Environment variable name.
            default: Default value if key is not present.

        Returns:
            Integer value or default.

        Raises:
            ValueError: If value cannot be converted to integer.
        """
        value = self._get_value(key)
        if value is None:
            return default
        return int(value)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value.

        Recognizes: 1, true, yes, on (case-insensitive) as True.
        All other values including empty string are False.

        Args:
            key: Environment variable name.
            default: Default value if key is not present.

        Returns:
            Boolean value or default.
        """
        value = self._get_value(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def require(self, key: str, cast: Callable[[str], Any] = str) -> Any:
        """Get required configuration value, raising error if missing.

        Args:
            key: Environment variable name.
            cast: Function to convert string value (default: str).

        Returns:
            Configuration value cast to desired type.

        Raises:
            MissingSettingError: If key is not present in environment.
        """
        value = self._get_value(key)
        if value is None:
            raise MissingSettingError(key)
        return cast(value)

    def as_dict(self) -> dict[str, str]:
        """Return effective environment as dictionary.

        Returns:
            Dictionary containing all environment variables,
            with overrides applied if present.
        """
        result = dict(os.environ)
        if self._overrides:
            result.update(self._overrides)
        return result

    def with_overrides(self, **overrides: str) -> RuntimeConfig:
        """Create new RuntimeConfig with temporary override values.

        This is useful for testing - creates an isolated config instance
        that sees override values without mutating global state.

        Args:
            **overrides: Key-value pairs to override.

        Returns:
            New RuntimeConfig instance with overrides applied.
        """
        # Merge existing overrides with new ones
        merged = dict(self._overrides) if self._overrides else {}
        merged.update(overrides)

        new_config = RuntimeConfig(overrides=merged)
        new_config._loaded = self._loaded
        return new_config

    @contextmanager
    def override(self, overrides: dict[str, str]) -> Iterator[None]:
        """Context manager to temporarily override configuration values.

        This modifies the config instance in-place for the duration of
        the context, then restores original state.

        Args:
            overrides: Dictionary of temporary override values.

        Yields:
            None
        """
        # Save original state
        original_overrides = self._overrides
        original_env = {}

        try:
            # Apply overrides to actual environment
            for key, value in overrides.items():
                if key in os.environ:
                    original_env[key] = os.environ[key]
                os.environ[key] = value

            # Create override mapping
            if original_overrides:
                merged = dict(original_overrides)
                merged.update(overrides)
                self._overrides = MappingProxyType(merged)
            else:
                self._overrides = MappingProxyType(overrides)

            yield

        finally:
            # Restore original state
            self._overrides = original_overrides

            # Restore environment
            for key in overrides:
                if key in original_env:
                    os.environ[key] = original_env[key]
                else:
                    os.environ.pop(key, None)


# Singleton instance for runtime use
runtime_config = RuntimeConfig()
