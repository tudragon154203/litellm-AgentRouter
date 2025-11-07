# Agent Guidelines

- Prioritize a TDD mindset even when authoring specs: capture expected behaviors, tests, and coverage goals before describing implementation details.
- When delivering work, outline the tests that must be written and ensure they are executed first; only proceed to implementation once failing tests exist.
- Check lint status first with `_flake8.ps1`; if issues appear, run `_autopep8.ps1`, apply any remaining manual fixes, then rerun `_flake8.ps1` to confirm a clean result before handoff.
- Maintain code coverage above 95%. If new work threatens this threshold, expand tests until the target is met.
- Create empty `__init__.py` files in new Python packages/directories to ensure proper module recognition.
- Avoid `__all__` or explicit export statements at the end of Python files; rely on natural module structure.
- Use descriptive variable names that clearly indicate their purpose and data type (e.g., `user_id` instead of `uid`, `is_authenticated` instead of `auth`).
- Document any assumptions, verification steps, and follow-up actions so future agents can continue seamlessly.
- Prefer using centralized config src\config\config.py instead of os.getenv

## Architecture Knowledge

- The project uses a modular architecture with clear separation: `src/config/` for configuration logic, `src/telemetry/` for observability, and core modules (`main.py`, `proxy.py`, `cli.py`, `utils.py`) for orchestration.
- Configuration flows through: environment loading → CLI parsing → YAML generation → proxy startup. Always respect this pipeline when making changes.
- The proxy wraps LiteLLM and exposes an OpenAI-compatible API. Changes to model handling should consider both LiteLLM's capabilities and OpenAI client expectations.
- Telemetry uses FastAPI middleware patterns. When adding instrumentation, follow the existing middleware structure in `src/telemetry/middleware.py`.

## Common Patterns

- Use context managers for temporary files and resources (see `utils.py` for examples).
- Model specifications are defined in `src/config/models.py` as `ModelSpec` dataclasses. Always validate new model additions against this structure.
- Environment variable parsing follows the pattern: `MODEL_<KEY>_<PROPERTY>` for multi-model configs. Maintain this convention for consistency.
- Import style: Use `from __future__ import annotations` for type hints, prefer explicit imports over wildcards, use relative imports within `src/`.

## Testing Strategy

- Unit tests go in `tests/unit/`, integration tests in `tests/integration/`.
- Mock external dependencies in unit tests (LiteLLM, HTTP clients, file I/O).
- Integration tests should check for required environment variables and skip gracefully if missing.
- Use `pytest-mock` for mocking, `pytest-cov` for coverage reporting.
- Run full test suite with `pytest` before considering work complete.

## Docker & Deployment

- The Docker setup uses volume mounts for live reloading during development (`docker-compose.yml`).
- Production image uses editable install (`pip install -e .`) to support hot-reloading.
- Environment variables can be passed via `.env` files or `--env-file` flag.
- The entrypoint script (`entrypoint.sh`) handles signal forwarding and graceful shutdown.

## Debugging & Troubleshooting

- Check `htmlcov/index.html` for coverage reports after running tests.
- Use `--print-config` flag to debug configuration generation without starting the proxy.
- Telemetry logs are structured JSON - parse them for debugging request flows.
- When proxy startup fails, check: environment variables, model API keys, LiteLLM version compatibility.
