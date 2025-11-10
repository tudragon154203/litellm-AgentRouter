# Claude Agent Playbook

- Start every task by clarifying expected tests and success criteria; draft the test list before touching implementation.
- Execute `_flake8.ps1` at the outset to understand current lint status; rerun after changes to ensure no regressions.
- Use `_autopep8.ps1` to auto-format prior to manual lint corrections, then rerun `_flake8.ps1` and resolve any remaining warnings.
- Keep overall coverage above 95% by writing targeted tests alongside code changes.
- Create empty `__init__.py` files in new Python packages/directories to ensure proper module recognition.
- Avoid `__all__` or explicit export statements at the end of Python files; rely on natural module structure.
- Use descriptive variable names that clearly indicate their purpose and data type (e.g., `user_id` instead of `uid`, `is_authenticated` instead of `auth`).
- Record assumptions, outstanding questions, and follow-up items so the next contributor (human or agent) has full context.
- Prefer using centralized config src\config\config.py instead of os.getenv
- Source code should follow SOLID principles

## Codebase Familiarity

- This is a Python 3.8+ project using LiteLLM as the core dependency for multi-model proxy functionality.
- The codebase has been refactored from monolithic modules into focused subsystems (`config/`, `telemetry/`).
- Test coverage is comprehensive (95%+) and must be maintained with any changes.
- The project uses PowerShell scripts for common tasks on Windows (`_flake8.ps1`, `_autopep8.ps1`, `_restart.ps1`).

## Key Concepts

- **Model Specs**: Defined in `src/config/models.py`, these describe model capabilities (reasoning support, parameter filtering).
- **Reasoning Effort**: Some models (DeepSeek, GPT-5) support reasoning effort controls via custom parameters.
- **Alias Lookup**: The telemetry system resolves model aliases to canonical names for consistent logging.
- **Multi-Model Config**: A single proxy instance can expose multiple models simultaneously using the `PROXY_MODEL_KEYS` pattern.

## When Making Changes

- Always check if changes affect the configuration pipeline (env → CLI → YAML → proxy).
- Consider backward compatibility with existing `.env` files and CLI usage patterns.
- Update both unit and integration tests when adding new model support or features.
- Verify that generated YAML configs use `os.environ/VAR_NAME` references for secrets (not hardcoded values).