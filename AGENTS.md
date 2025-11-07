# Agent Guidelines

## Development Workflow

- Prioritize a TDD mindset: capture expected behaviors, tests, and coverage goals before implementation.
- When delivering work, write failing tests first, then implement to make them pass.
- Check lint status with `_flake8.ps1`; if issues appear, run `_autopep8.ps1`, apply manual fixes, then rerun `_flake8.ps1` to confirm clean status.
- Maintain code coverage above 95%. Expand tests if new work threatens this threshold.
- Create empty `__init__.py` files in new Python packages/directories for proper module recognition.
- Avoid `__all__` or explicit export statements; rely on natural module structure.
- Use descriptive variable names (e.g., `user_id` not `uid`, `is_authenticated` not `auth`).
- Document assumptions, verification steps, and follow-up actions for future agents.

## Architecture Knowledge

- Modular architecture: `src/config/` for configuration, `src/telemetry/` for observability, `src/logging/` for structured logging, core modules (`main.py`, `proxy.py`, `cli.py`, `utils.py`) for orchestration.
- Configuration flow: environment loading → CLI parsing → centralized config initialization → YAML generation → proxy startup. Respect this pipeline.
- The proxy wraps LiteLLM and exposes an OpenAI-compatible API. Consider both LiteLLM capabilities and OpenAI client expectations.
- Telemetry uses FastAPI middleware patterns. Follow existing structure in `src/telemetry/middleware.py`.

## Common Patterns

- Use context managers for temporary files and resources (see `utils.py`).
- Model specifications are `ModelSpec` dataclasses in `src/config/models.py`. Validate new models against this structure.
- Environment variable pattern: `MODEL_<KEY>_<PROPERTY>` for multi-model configs. Maintain this convention.
- Import style: Use `from __future__ import annotations`, prefer explicit imports over wildcards, use relative imports within `src/`.
- Configuration access: Use centralized `src/config/config.py` instead of direct `os.getenv()` calls.
- Multi-upstream support: Models can have multiple upstream providers via `MODEL_<KEY>_UPSTREAMS` comma-separated list.

## Testing Strategy

- Unit tests in `tests/unit/`, integration tests in `tests/integration/`.
- Mock external dependencies in unit tests (LiteLLM, HTTP clients, file I/O).
- Integration tests check for required environment variables and skip gracefully if missing.
- Use `pytest-mock` for mocking, `pytest-cov` for coverage reporting.
- Run full test suite with `pytest` before considering work complete.

## Docker & Deployment

- Docker setup uses volume mounts for live reloading (`docker-compose.yml`).
- Production image uses editable install (`pip install -e .`) for hot-reloading.
- Environment variables via `.env` files or `--env-file` flag.
- Entrypoint script (`entrypoint.sh`) handles signal forwarding and graceful shutdown.

## Debugging & Troubleshooting

- Check `htmlcov/index.html` for coverage reports after running tests.
- Use `--print-config` flag to debug configuration generation without starting proxy.
- Telemetry logs are structured JSON - parse them for debugging request flows.
- Proxy startup failures: check environment variables, model API keys, LiteLLM version compatibility.
