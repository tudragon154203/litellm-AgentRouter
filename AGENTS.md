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
