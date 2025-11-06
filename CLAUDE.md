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