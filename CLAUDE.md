# Claude Agent Playbook

- Start every task by clarifying expected tests and success criteria; draft the test list before touching implementation.
- Execute `_flake8.ps1` at the outset to understand current lint status; rerun after changes to ensure no regressions.
- Use `_autopep8.ps1` to auto-format prior to manual lint corrections, then rerun `_flake8.ps1` and resolve any remaining warnings.
- Keep overall coverage above 95% by writing targeted tests alongside code changes.
- Record assumptions, outstanding questions, and follow-up items so the next contributor (human or agent) has full context.
