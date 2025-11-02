# src Package Refactor PRD

## Background
- The current `src/` package is a flat module namespace (`src.main`, `src.cli`, `src.config`, etc.), so imports leak internal boundaries and complicate dependency management.
- Tests, demos, and scripts reach into these flat modules directly, making refactors risky and leading to tight coupling between unrelated components.
- Packaging metadata (`pyproject.toml`, `entrypoint.sh`) still assumes the `src.*` path, blocking clearer module responsibilities or guard rails.
- Recent scanning shows oversized modules such as `src/telemetry.py` (447 LOC) and `src/config.py` (322 LOC) that mix multiple concerns and violate the single-responsibility target we want for SOLID compliance.

## Goals
- Decompose the bloated modules in `src/` into cohesive submodules so CLI, config, proxy, telemetry, and utility concerns have explicit boundaries while the public interfaces stay stable.
- Define and document the supported public entrypoints (e.g., `src.cli.main`, `src.config.prepare_config`, telemetry middleware factories) and ensure tests exercise only those contracts.
- Update every test, fixture, and helper to encode the desired module responsibilities so they fail until the refactor enforces SOLID boundaries.
- Provide migration notes in specs/docs that call out any breaking changes and how downstream code should adapt to the refined module surfaces.

## Non-Goals
- No feature work on proxy behavior, telemetry semantics, CLI flags, or environment parsing—only responsibility partitioning and import hygiene.
- No introduction of a brand-new top-level package; work happens within `src/` while making responsibilities clearer.
- No packaging or publishing workflow changes beyond what is required to point entrypoints at the updated modules.

## Users & Scenarios
- **Maintainer refactoring configuration code**: wants clearly scoped modules (`src.config`, `src.cli`) to reason about dependencies and extend functionality without stepping on unrelated logic.
- **Test author**: needs imports that mirror the refined structure to keep unit and integration tests aligned with real execution paths.
- **External contributor**: expects a predictable package namespace that mirrors the documentation and avoids ambiguous `src.` imports into internal helpers.
- **CI/CD tooling**: relies on entrypoints defined in `pyproject.toml` and shell scripts; after the refactor, pipelines must still start the launcher via the stable module paths.

## Expected Behaviors (TDD Anchors)
- Importing runtime components via the documented `src.*` modules succeeds and exposes the same callable interfaces (`main`, `parse_args`, `prepare_config`, `start_proxy`, telemetry middleware helpers, etc.).
- Tests fail fast if they attempt to import internal-only helpers, signaling where SOLID boundaries need reinforcement.
- Test suites instantiate CLI, configuration, proxy, and telemetry flows exclusively through the refined module surfaces.
- Packaging entrypoints invoke the stabilized modules without runtime import failures.
- Coverage for the reorganized modules remains ≥95% after refactor-specific tests are added.

## Test Plan (Write First)
- **New unit tests**:
  - `tests/unit/test_module_exports.py`: validate that each public module exposes the documented entrypoints and that importing them yields callables wired to the refactored code.
  - `tests/unit/test_internal_imports.py`: assert that attempting to reach private helpers directly raises the expected errors (or is blocked by private naming conventions).
  - Update existing unit suites (CLI, config, proxy, telemetry, utils) to import from the refined module surfaces before implementation begins; they will fail until the refactor is complete.
- **Integration tests**:
  - Adjust all integration fixtures to load helpers through the stabilized module paths and ensure startup flows (e.g., `tests/integration/test_multi_model_integration.py`) reference the documented entrypoints.
  - Add an integration guard verifying `python -m src.main` (or the preferred launcher module) boots successfully using the refactored surfaces.
- **Coverage gates**:
  - Ensure refactor-focused tests exercise each reorganized module so overall coverage remains above 95%. Add targeted assertions around proxy startup, CLI parsing, and telemetry instrumentation to avoid coverage regressions.
- Execute `_flake8.ps1` (or a documented fallback) and `pytest --cov` once the new tests are in place and failing, before making implementation changes.

## Functional Requirements
1. Break down oversized modules (currently `src/telemetry.py`, `src/config.py`, `src/cli.py`, `src/utils.py`) into smaller SOLID-aligned components while keeping public entrypoints stable.
2. Update module interfaces to expose documented entrypoints (`main()`, `parse_args()`, `prepare_config()`, `start_proxy()`, telemetry middleware constructors, etc.) through explicit exports or factories.
3. Use private naming conventions (leading underscore) for internal helpers so tests and downstream code cannot depend on private implementation details.
4. Adjust packaging metadata (`pyproject.toml`, console scripts, `entrypoint.sh`, Dockerfile, etc.) only where necessary to reference the refined modules.
5. Update all test imports and helpers to use the public module surfaces and ensure they exercise the reorganized responsibilities.
6. Provide clear developer-facing notes describing responsibility boundaries and any breaking changes so downstream consumers update their imports.

## Non-Functional Requirements
- Preserve lint cleanliness (flake8) and typing expectations once implementation completes.
- Maintain current runtime performance characteristics; refactor must not add significant import overhead or circular dependencies.
- Keep logging, error handling, and telemetry outputs unchanged aside from import-path adjustments that enforce SOLID responsibilities.
- Document the responsibility boundaries prominently so future contributors understand the structure.
- Keep all `__init__.py` files empty so packages expose behavior only through explicit module exports.

## Implementation Notes (Guidance Only)
- Introduce focused submodules inside `src/` (e.g., `src/telemetry/logger.py`, `src/config/models.py`) to isolate responsibilities without creating a brand-new top-level package.
- Migrate common helpers from `src/utils.py` into narrower modules so calling code depends only on the abstractions it needs.
- Ensure relative imports between submodules remain acyclic; prefer explicit imports that make dependencies obvious.
- Remove obsolete code paths uncovered during decomposition (e.g., unused telemetry helpers) to reduce module size.
- Update build scripts and documentation only where the refined module names change the expected invocation command.

## Migration & Documentation
- Update `README.md`, `AGENTS.md`, `CLAUDE.md`, and any quickstart guides to reference the stabilized module imports and entrypoints.
- Provide a migration table in docs mapping old internal helper usage to the new public abstractions or advising replacements.
- Call out in release notes that responsibility boundaries tightened and that direct imports of internal helpers may now fail.

## Milestones
1. **Spec & Test Authoring** (0.5 day): land the failing tests, updated fixtures, and documentation placeholders capturing the new module responsibilities.
2. **Module Decomposition** (1.0 day): split code into cohesive submodules, guard internal helpers, and update entrypoints.
3. **Docs & Cleanup** (0.5 day): refresh documentation, finalize migration guidance, rerun lint/tests, and ensure coverage ≥95%.

## Acceptance Criteria
- Running unit and integration suites after the refactor shows tests importing only the documented `src.*` surfaces, with zero reliance on private helpers.
- Attempts to import internal-only helpers fail (or trigger clear warnings), and docs highlight the supported entrypoints.
- Entry points defined in `pyproject.toml` and shell scripts execute without import errors using the refined modules.
- Linting (`_flake8.ps1` or fallback) passes, and `pytest --cov` reports ≥95% coverage.

## TODO (TDD Checklist)
- [ ] Author new unit tests for public module exports and internal import guards.
- [ ] Update existing tests to target the refined `src.*` namespace.
- [ ] Add integration guard ensuring CLI/proxy startup works through the documented entrypoints.
- [ ] Implement the module decomposition and guard internal helpers.
- [ ] Refresh documentation and tooling references to the refined structure.
- [ ] Verify lint (`_flake8.ps1` or fallback) and `pytest --cov` both pass with coverage ≥95%.
