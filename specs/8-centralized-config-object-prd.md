# Centralized Config Object PRD

## Overview
The LiteLLM launcher currently exposes `load_dotenv_files()` in `src/utils.py`, and both runtime code (`src/main.py`) and multiple test modules (`tests/integration/conftest.py`, real API smoke tests, startup tests) call it directly or manipulate `os.environ`. This scattering makes it easy to forget to load `.env` files, complicates test setup, and tightly couples callers to dotenv semantics. We need a single configuration surface that eagerly loads `.env` once, exposes typed accessors, and can be reused across `src/` and `tests/` without re-importing `.env` helpers.

**Central Goal**: Introduce a centralized configuration object that is responsible for reading `.env` (respecting `SKIP_DOTENV`), validating required keys, and providing accessor helpers. After this work, no other module—production or test—should call `load_dotenv_files()` or manually read `.env`; everything should depend on the shared config API.

## Current State
- `.env` handling lives in `src/utils.load_dotenv_files()`. Callers manually invoke it during startup and in tests.
- Tests directly mutate `os.environ` and individually call `load_dotenv_files()`, duplicating setup logic.
- Configuration concerns (parsing env, providing defaults, validation) are spread across CLI parsing, test fixtures, and ad-hoc helpers.
- There is no single source of truth for environment-derived settings, making it hard to reason about guarantees or extend configuration safely.

## User Stories
- *Runtime maintainer* wants to initialize the proxy with one import (`from src.config.env import runtime_config`) and know `.env` is loaded exactly once.
- *QA engineer* needs deterministic tests that rely on a shared config fixture instead of reloading `.env` per test module.
- *Contributor* wants obvious extension points for new environment variables without editing multiple files or remembering bespoke loaders.
- *Operations engineer* needs reliable validation messages when required env vars are missing or malformed, without reading internal test utilities.

## Functional Requirements
1. **Central Config Module** (`src/config/config.py`):
   - Provides a singleton-style object (e.g. `RuntimeConfig`) that loads `.env` on first import unless `SKIP_DOTENV` is set.
   - Offers typed accessors for known settings (host, port, model keys, API keys, etc.) and passes through arbitrary keys via `__getitem__` for backwards compatibility.
   - Exposes helper constructors (e.g. `from_environ`, `with_overrides`) to support tests without mutating global state.
   - Emits clear errors when required keys are missing; respects existing defaults used across CLI parsing.

2. **Test Utilities** (`tests/conftest.py` or dedicated fixtures):
   - Provide a fixture that yields an isolated config instance with temporary env overrides (uses temporary `.env` or `monkeypatch` under the hood, but never calls `load_dotenv_files()` directly).
   - Ensure integration tests relying on real APIs still go through the config object for `.env` population.

3. **Deprecate Direct Calls**:
   - `src/main.py` and any other runtime module must import and use the new config object. The only remaining reference to `load_dotenv_files()` should live inside the config module itself (or be retired entirely).
   - Tests (`tests/integration/api/test_real_*`, `tests/integration/conftest.py`, startup tests) must stop importing `load_dotenv_files()` and instead leverage fixtures/helpers from the new config surface.
   - Static analysis (`rg "load_dotenv_files"`) should return only the central module and its tests after refactor.

4. **Documentation & Examples**:
   - Update `README.md` and `.env.example` to describe the new config entry point, including how tests should consume it.
   - Document how `SKIP_DOTENV` interacts with the config object.
   - Describe extension guidelines (where to add new keys, validation rules).

## Non-Functional Requirements
- Maintain ≥95% test coverage; add coverage for new config behaviors where needed.
- Preserve startup latency; loading `.env` once must not add noticeable overhead.
- Keep API backwards compatible for existing CLI workflows (command-line arguments should still override env-derived defaults).
- Conform to `_flake8.ps1`; update formatting if `_autopep8.ps1` is needed.

## Test Strategy (TDD First)
1. **Unit Tests** (write before implementation, expect failures):
   - `tests/unit/config/test_config_runtime.py`: verify singleton behavior, `.env` loading, `SKIP_DOTENV` handling, typed accessors, error messages, and override helper semantics.
   - `tests/unit/startup/test_main.py`: update/extend tests to assert `main()` retrieves configuration via the new object rather than calling `load_dotenv_files()`.
2. **Integration Tests**:
   - Modify `tests/integration/conftest.py` to use the config fixture; add regression coverage that `.env` values become visible to API tests without manual loading.
   - Ensure real API tests (`tests/integration/api/test_real_*.py`) import the config fixture/path.
3. **Regression Guard**:
   - Add a `rg`-backed test or lint step (e.g. `tests/unit/package/test_module_exports.py`) asserting `load_dotenv_files` is not used outside the config module once migration completes.

## Implementation Plan (High-Level)
1. Draft failing tests capturing the desired config API and the absence of direct `load_dotenv_files()` usage.
2. Implement the central config module with `.env` loading, caching, typed accessors, and override helpers.
3. Refactor runtime entry points (`src/main.py`, any other consumers) to rely on the new config interface.
4. Update test fixtures and integration tests to use the shared config instead of manual env manipulation.
5. Remove or internalize `load_dotenv_files()`; ensure legacy imports fail fast with guidance or re-export a backwards-compatible shim that delegates to the new module (pending decision during implementation).
6. Refresh documentation and sample configs.

## Detailed Design
- **Module Layout**
  - Create `src/config/config.py` exporting:
    - `RuntimeConfig`: primary configuration object.
    - `MissingSettingError`: raised when required keys are missing.
    - `runtime_config`: eagerly constructed singleton used by runtime code.
  - Update `src/config/__init__.py` to re-export `runtime_config` for ergonomic imports while avoiding circular imports.
  - Keep legacy `src.utils.load_dotenv_files` as a thin compatibility wrapper that calls `runtime_config.ensure_loaded()`; mark it with a deprecation docstring to steer callers away.

- **RuntimeConfig Responsibilities**
  - On initialization, compute dotenv search paths (`Path(__file__).resolve().parent.parent / ".env"` and `Path.cwd() / ".env"`) matching the current loader behavior (observed in `src/utils.py`).
  - Expose `ensure_loaded()` that performs idempotent dotenv loading unless `SKIP_DOTENV` is set; store a `_loaded` boolean to prevent duplicate reads.
  - Implement typed accessors:
    - `get_str(key, default=None)`, `get_int(key, default=None)`, `get_bool(key, default=None)` reusing `env_bool` semantics so callers do not import `src.utils`.
    - `require(key, cast=str)` that raises `MissingSettingError` when absent.
  - Provide overlay helpers for tests:
    - `with_overrides(**values)` returns a new `RuntimeConfig` sharing the loader but using an immutable `MappingProxyType` for overrides before falling back to `os.environ`.
    - `override(overrides)` context manager that temporarily mutates the singleton and restores state on exit (backed by `contextlib.ExitStack`) for compatibility with fixtures.
  - Surface the effective environment via `as_dict()` for components like `prepare_config` that expect a `dict[str, str]`.

- **Runtime Integration**
  - Replace direct `load_dotenv_files()` call in `src/main.py` with `runtime_config.ensure_loaded()`; pass the resulting config (or accessor methods) into `validate_prereqs`, CLI parsing, and `prepare_config` as needed.
  - Audit other runtime modules (`src/proxy`, `src/config/parsing`, middleware) to determine whether they should read directly from `runtime_config` or continue using `os.getenv`. At a minimum, `prepare_config.load_model_specs_from_env` should read from the injected config object to enable deterministic tests.

- **Testing & Fixtures**
  - Introduce `tests/unit/config/test_config_runtime.py` covering loader behavior, typed accessors, overrides, and `SKIP_DOTENV` short-circuiting.
  - Update `tests/integration/conftest.py` session fixture to simply call `runtime_config.ensure_loaded()` instead of importing `load_dotenv_files`.
  - Provide a pytest fixture (e.g. `config_overrides`) under `tests/conftest.py` that uses `runtime_config.override({...})` to isolate environment-dependent tests.
  - Update `tests/unit/startup/test_main.py` mocks to patch `runtime_config.ensure_loaded` instead of `load_dotenv_files`, preserving existing call-order assertions.
  - Extend `tests/unit/package/test_module_exports.py` to assert that `src.config.config` exports `runtime_config` and that `src.utils.load_dotenv_files` is available but marked deprecated.

- **Migration Strategy**
  - `rg "load_dotenv_files"` after refactor should only hit the compatibility shim and its tests. Add a regression assertion in `tests/unit/package/test_module_exports.py` to guard against new direct usages.
  - Document the new import path (`from src.config.config import runtime_config`) in `README.md` and `.env.example`.
  - Ensure `RuntimeConfig.ensure_loaded()` is safe under multiprocessing/threading scenarios used by integration tests (idempotent check + threading lock if contention appears during implementation).

## Risks & Mitigations
- **Global State Coupling**: Singleton configs can leak state between tests. Mitigate by providing explicit factory/override helpers and fixtures that reset state.
- **Hidden Consumers**: Some downstream scripts may import `load_dotenv_files()` directly. Add clear deprecation path and search the repo (`rg`) during implementation to catch stragglers.
- **Real API Credentials**: Integration tests rely on real credentials. Ensure the config object defers to existing environment variables so CI remains unaffected.
- **Circular Imports**: Moving env handling into `src/config` may introduce cycles. Keep utilities pure and avoid importing heavy runtime modules inside the config file.

## Verification Steps
```bash
# 1. Create failing tests first
pytest tests/unit/config/test_config_runtime.py -k "RuntimeConfig"  # new tests
pytest tests/unit/startup/test_main.py::TestMainStartup  # updated expectation

# 2. After implementation
pytest  # full suite
pytest --cov=src --cov-report=term-missing
./_flake8.ps1
```

## Assumptions
- No external module (outside this repository) relies on `src.utils.load_dotenv_files` as a public API. If discovered otherwise, we will provide a compatibility wrapper with deprecation warnings.
- `.env` files will remain small enough to load synchronously during import without impacting startup deadlines.
- Tests can use `monkeypatch` or temporary directories to simulate `.env` content without requiring file I/O in disallowed locations.

## Follow-Up Opportunities
- Collect all configuration defaults and validation logic into a schema-driven system (e.g. `pydantic` or dataclasses).
- Introduce CLI subcommand (`python -m src.config.env dump`) to print effective configuration for debugging.
- Evaluate removing the legacy `.env` loader entirely once all consumers rely on the new interface.
