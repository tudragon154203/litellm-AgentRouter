# Claude Agent Playbook

## Development Workflow

- Start every task by clarifying expected tests and success criteria; draft the test list before touching implementation.
- Execute `_flake8.ps1` at the outset to understand current lint status; rerun after changes to ensure no regressions.
- Use `_autopep8.ps1` to auto-format prior to manual lint corrections, then rerun `_flake8.ps1` and resolve any remaining warnings.
- Keep overall coverage above 95% by writing targeted tests alongside code changes.
- Create empty `__init__.py` files in new Python packages/directories to ensure proper module recognition.
- Avoid `__all__` or explicit export statements; rely on natural module structure.
- Use descriptive variable names (e.g., `user_id` not `uid`, `is_authenticated` not `auth`).
- Record assumptions, outstanding questions, and follow-up items for the next contributor.
- Use centralized `src/config/config.py` instead of direct `os.getenv()` calls.

## Codebase Familiarity

- Python 3.8+ project using LiteLLM v1.78.7 as the core dependency for multi-model proxy functionality.
- Modular architecture with focused subsystems: `src/config/`, `src/telemetry/`, `src/logging/`.
- Test coverage is comprehensive (95%+) and must be maintained with any changes.
- PowerShell scripts for common tasks on Windows: `_flake8.ps1`, `_autopep8.ps1`, `_restart.ps1`.

## Key Concepts

- **Model Specs**: Defined in `src/config/models.py`, these describe model capabilities (reasoning support, parameter filtering).
- **Reasoning Effort**: Some models (DeepSeek, GPT-5) support reasoning effort controls via custom parameters.
- **Alias Lookup**: The telemetry system resolves model aliases to canonical names for consistent logging.
- **Multi-Model Config**: A single proxy instance can expose multiple models simultaneously using the `PROXY_MODEL_KEYS` pattern.
- **Multi-Upstream Support**: Models can have multiple upstream providers via `MODEL_<KEY>_UPSTREAMS` comma-separated list.
- **Centralized Config**: The `src/config/config.py` singleton provides centralized access to configuration values.
- **Structured Logging**: The `src/logging/` subsystem provides console and in-memory logging with structured output.

## When Making Changes

- Always check if changes affect the configuration pipeline: env loading → CLI parsing → centralized config → YAML generation → proxy startup.
- Consider backward compatibility with existing `.env` files and CLI usage patterns.
- Update both unit and integration tests when adding new model support or features.
- Verify that generated YAML configs use `os.environ/VAR_NAME` references for secrets (not hardcoded values).
- Integration tests should check for required environment variables and skip gracefully if missing.
- Use the centralized config singleton for accessing configuration values throughout the codebase.