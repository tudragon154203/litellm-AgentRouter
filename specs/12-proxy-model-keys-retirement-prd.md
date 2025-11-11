# PROXY_MODEL_KEYS Retirement PRD

## Background
- Multi-model setups currently require `PROXY_MODEL_KEYS` plus `MODEL_<KEY>_*` variables, forcing operators to maintain two sources of truth just to declare models.
- Ordering is brittle: typos or mismatched counts between `PROXY_MODEL_KEYS` and the per-model variables cause runtime failures that are hard to diagnose.
- The upcoming alias-unification effort already reduces env surface area; keeping `PROXY_MODEL_KEYS` contradicts that simplification and clutters docs, tests, and entrypoint logic.
- CI and local `.env` files now repeat every model key twice, slowing onboarding and creating noise in reviewed diffs.
- Goal: infer active models directly from the `MODEL_<KEY>_UPSTREAM_MODEL` namespace so configuration remains declarative without an additional global switch.

- Autodiscover the complete set of model keys from environment variables without relying on `PROXY_MODEL_KEYS`.
- Maintain deterministic, alphabetical ordering (stable between restarts) across all surfaces (config output, `/models`, telemetry) without introducing per-model `_ORDER` variables.
- Gracefully ignore any `PROXY_MODEL_KEYS` value (optionally logging a warning) so legacy configs continue to boot without relying on it.
- Keep the environment → config → proxy pipeline unchanged for consumers: once specs are parsed, downstream CLI/YAML/entrypoint behavior must match historical expectations.
- Ensure docs, samples, and tooling consistently describe the new schema.

## Non-Goals
- No redesign of CLI `--model-spec` handling; CLI input already lists specs explicitly and should remain unchanged.
- No compatibility shim that reuses `PROXY_MODEL_KEYS` for ordering; the variable may be read only to emit warnings before being ignored.
- No broader refactor of telemetry, routing, or LiteLLM adapter logic beyond what is needed to remove the dependency on `PROXY_MODEL_KEYS`.

## Users & Scenarios
- **Platform operator**: wants to declare `MODEL_GPT5_UPSTREAM_MODEL=gpt-5` and `MODEL_DEEPSEEK_UPSTREAM_MODEL=deepseek-v3.2` without editing a separate key list; expects the proxy to expose both models immediately in alphabetical order.
- **CI author**: writes fixtures that set only the variables under test. Removing `PROXY_MODEL_KEYS` lowers fixture verbosity and reduces failure modes from forgetting to update both places.
- **Doc consumer**: expects `.env` examples to scale linearly with the number of models and avoid extraneous knobs.
- **On-call responder**: prefers startup to proceed even if `PROXY_MODEL_KEYS` lingers; a warning message should flag the deprecated variable without blocking remediation steps.

## Functional Requirements
1. `load_model_specs_from_env` must:
   - Scan all environment variables matching `MODEL_<KEY>_UPSTREAM_MODEL`.
   - Build each `ModelSpec` exclusively from the namespaced variables for that key.
   - Sort the resulting model specs alphabetically by key to provide deterministic ordering everywhere.
2. If `PROXY_MODEL_KEYS` is present (even empty), the parser must ignore it entirely while emitting a clear warning (stderr log, telemetry, or both) so operators know the variable no longer has effect.
3. The CLI `--print-config` path, YAML renderer, and `/models` endpoint must receive model specs in the resolved alphabetical order so downstream configs (and OpenAI-compatible listings) remain predictable.
5. Entry point validation (Python and shell/PowerShell) should rely on the autodiscovery logic; error messaging must guide users to declare at least one `MODEL_<KEY>_UPSTREAM_MODEL`.
6. Docs (`README.md`, `.env` samples, CLAUDE.md, docker-compose) must illustrate model declaration without `PROXY_MODEL_KEYS` and describe the default alphabetical ordering behavior.
7. Tests must cover single-model, multi-model, and alphabetical ordering scenarios, including failure when no model vars exist.
8. `src/config/config.py` should continue to source provider defaults (API keys, base URLs) from centralized config while iterating the discovered keys; no direct `os.getenv` calls outside the config layer.
9. Removing `PROXY_MODEL_KEYS` must not drop overall code coverage below 95%; add tests as needed.

## Non-Functional Requirements
- Maintain lint cleanliness by running `_flake8.ps1`; auto-fix via `_autopep8.ps1` only if necessary.
- Provide actionable exception messages when misconfigured (missing models) and clear warnings when `PROXY_MODEL_KEYS` lingers.
- Preserve startup performance; autodiscovery is a one-time lightweight regex/parse pass.
- Follow existing SOLID/module boundaries (env parsing confined to `src/config/parsing.py`, orchestration in `src/config/entrypoint.py`, etc.).

## Proposed Solution
### Environment Autodiscovery
- Implement helper `discover_model_keys()` inside `src/config/parsing.py`:
  - Iterate over `os.environ`, matching `MODEL_(?P<key>[A-Z0-9_]+)_UPSTREAM_MODEL`.
  - Normalize keys to uppercase and de-duplicate.
  - Return keys sorted alphabetically to enforce deterministic ordering.
- Update `load_model_specs_from_env` to call this helper; if the returned list is empty, raise `ValueError("At least one MODEL_<KEY>_UPSTREAM_MODEL must be set")`.
- If `PROXY_MODEL_KEYS` exists in env, log a warning (`"PROXY_MODEL_KEYS is ignored; rely on MODEL_<KEY>_UPSTREAM_MODEL declarations."`) but continue parsing discovered model specs.

### Entrypoint & Runtime Config
- Replace `runtime_config.get_str("PROXY_MODEL_KEYS")` usage in `src/config/entrypoint.py` with `discover_model_keys()`.
- PowerShell and shell entrypoint scripts should call the Python helper (via `python -m src.config.entrypoint --print-config`) instead of duplicating parsing logic, ensuring a single source of truth.

### CLI / Config Rendering
- `src/main.py` already accepts `--model-spec` multiple times; ensure env-parsed specs append ahead of CLI overrides in the same deterministic order.
- YAML generator (`prepare_config`) should preserve the order returned by the parser, so existing tests that assert list order continue to pass.

### Telemetry & Downstream Modules
- No code changes expected, but add regression tests to confirm telemetry still logs `ModelSpec.alias`.
- Ensure the instrumentation path does not assume `PROXY_MODEL_KEYS`.

### Documentation & Migration
- Update README, CLAUDE.md, sample `.env`, docker-compose instructions, and prior PRDs referencing `PROXY_MODEL_KEYS`.
- Add a migration section calling out:
  1. `PROXY_MODEL_KEYS` is ignored and can be removed at the operator’s convenience.
  2. Ensure each model declares `MODEL_<KEY>_UPSTREAM_MODEL` (+ optional options).
  3. Alphabetical sorting is now the only supported ordering mechanism; operators cannot influence order via env vars.

## Testing Strategy (TDD)
1. **Author failing tests first**:
   - `tests/unit/config/parsing/test_env_loading.py`: new cases for autodiscovery, alphabetical ordering, and verifying warnings when `PROXY_MODEL_KEYS` is set.
   - `tests/unit/deployment/test_entrypoint_sh.py` & `tests/unit/config/test_entrypoint.py`: validate entrypoint warning/ignore behavior for `PROXY_MODEL_KEYS` and success when only model env vars exist.
   - `tests/integration/multi_model/test_multi_model_integration.py`: assert alphabetical ordering flows through CLI/entrypoint/YAML.
   - `tests/integration/config/test_entrypoint_integration.py`: ensure `--print-config` works without `PROXY_MODEL_KEYS`.
2. Implement the autodiscovery logic and rerun the suite via `pytest --cov`.
3. Address lint via `_flake8.ps1` (and `_autopep8.ps1` if needed) before final verification.

## Milestones
1. **Design & Tests (0.5 day)**: Implement helper prototypes, draft failing tests covering autodiscovery, ordering, and legacy var warning/ignore behavior.
2. **Implementation (1 day)**: Update config loader, entrypoint, and scripts; ensure CLI/YAML pipelines consume the new helper and preserve alphabetical ordering.
3. **Docs & Cleanup (0.5 day)**: Refresh documentation, migration notes, and confirm lint/tests/coverage targets.

## Acceptance Criteria
- Starting the proxy with only `MODEL_PRIMARY_UPSTREAM_MODEL=gpt-5` succeeds; `PROXY_MODEL_KEYS` absence no longer errors.
- Adding multiple models (e.g., `MODEL_GPT5_UPSTREAM_MODEL`, `MODEL_DEEPSEEK_UPSTREAM_MODEL`) yields deterministic alphabetical ordering that the `/models` endpoint mirrors.
- Exporting `PROXY_MODEL_KEYS` has no effect beyond emitting a warning; model discovery still relies solely on `MODEL_<KEY>_UPSTREAM_MODEL`.
- Docs and sample `.env` files contain no references to `PROXY_MODEL_KEYS`; instructions explain optional ordering metadata.
- `_flake8.ps1` and `pytest --cov` pass with ≥95% coverage after the change set.

## TODO (TDD Checklist)
- [ ] Add failing unit tests for env autodiscovery, alphabetical ordering, and ensuring `PROXY_MODEL_KEYS` is ignored with a warning.
- [ ] Add failing integration tests covering multi-model alphabetical ordering and entrypoint behavior when `PROXY_MODEL_KEYS` is absent or still present.
- [ ] Implement autodiscovery helper, configuration loader changes, and entrypoint updates.
- [ ] Update docs, samples, and scripts to remove `PROXY_MODEL_KEYS`.
- [ ] Run `_flake8.ps1` (fix via `_autopep8.ps1` if necessary) and `pytest --cov` to confirm lint + coverage targets.
- [ ] Document migration guidance and verification steps in release notes / README for future agents.
