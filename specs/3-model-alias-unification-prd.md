# Model Alias Unification PRD

## Background
- LiteLLM launcher currently requires both `MODEL_<KEY>_ALIAS` and `MODEL_<KEY>_UPSTREAM_MODEL` when loading models from the multi-model environment schema.
- Downstream configuration (`model_list.model_name`) almost always mirrors the upstream model id, so operators duplicate the same string in two variables per model.
- Tests, documentation, and the Docker entrypoint still read `MODEL_*_ALIAS`, increasing the number of places we must maintain when onboarding new models.
- Goal: converge on a single `MODEL_<KEY>_UPSTREAM_MODEL` variable that feeds both the alias exposed by the proxy and the upstream LiteLLM target, eliminating redundant configuration.

## Goals
- Derive the public alias directly from the upstream model identifier without requiring a separate `MODEL_<KEY>_ALIAS` variable.
- Remove `MODEL_*_ALIAS` from environment parsing, entrypoint scaffolding, tests, and documentation with zero backward compatibility; startup should fail fast when legacy variables remain.
- Ensure CLI and programmatic configuration produce identical results when only `upstream` is supplied.
- Maintain existing behavior for reasoning effort, API key inheritance, and `openai/` prefix handling while simplifying the input surface.

## Non-Goals
- No redesign of alias customization beyond using the upstream model string (e.g., no new override like `MODEL_*_DISPLAY_NAME` in this iteration).
- No partial compatibility layer—legacy environment variables will be treated as invalid configuration.
- No changes to proxy runtime behavior beyond alias resolution (streaming, telemetry, routing remain untouched).

## Users & Scenarios
- **Operator adding a model**: wants to declare `MODEL_NEW_UPSTREAM_MODEL=deepseek-v3.2` and have the proxy expose `deepseek-v3.2` automatically.
- **CI engineer**: relies on environment fixtures in tests; removing redundant variables lowers setup errors and speeds up authoring new fixtures.
- **Doc consumer**: expects updated examples that only mention one env var per model, reducing cognitive load.
- **On-call responder**: benefits from consistent alias/upstream naming in telemetry logs without mismatches caused by typos across two variables.

## Functional Requirements
1. Environment loader (`load_model_specs_from_env`) must treat `MODEL_<KEY>_UPSTREAM_MODEL` as the single source of truth and populate both `ModelSpec.alias` and `ModelSpec.upstream_model` from it.
2. If any `MODEL_<KEY>_ALIAS` environment variable is detected, startup must raise a configuration error instructing users to remove the legacy variable.
3. CLI parsing (`--model-spec`) should allow omitting `alias`; when omitted, default alias = upstream model (after normalization). Explicit alias remains supported for advanced scenarios, but the configuration generator should document that env paths no longer support aliases.
4. Alias normalization must preserve common formats:
   - Strip leading `openai/` when deriving the alias so the public name matches current defaults (`gpt-5`, `deepseek-v3.2`).
   - When upstream contains vendor prefixes other than `openai/`, expose the suffix unless the CLI explicitly supplies an alias.
   - Retain original casing/spelling of the upstream identifier after normalization.
5. Config rendering (`render_model_entry`) and Docker entrypoint must continue to write `model_name` using the derived alias while keeping the upstream `model` field prefixed with `openai/` when required.
6. Update docs (`README.md`, `.env.example`) and samples to remove `MODEL_*_ALIAS` references and highlight the simplified schema.
7. Update Docker, tests, helper scripts, and sample environments so no code path references alias environment variables.
8. Expand unit/integration coverage to exercise:
   - Single-model env setup with only `MODEL_PRIMARY_UPSTREAM_MODEL`.
   - Multi-model env setup ensuring aliases mirror normalized upstream models.
   - CLI specs with and without explicit alias arguments.
   - Entry-point config generation path to confirm failure when legacy alias variables are present.
9. Integration telemetry/tests that assert alias→upstream mapping remain consistent after normalization (no regression for log output).
10. Any new or modified tests must keep overall project coverage ≥95%.

## Non-Functional Requirements
- Maintain zero-regression lint status (flake8) after changes; ensure new code paths respect existing style and typing expectations.
- Produce immediate, actionable error messages when legacy alias environment variables are encountered.
- Clearly document the breaking change so operators know to update their `.env` files before upgrading.
- Preserve performance characteristics; alias derivation should be a lightweight string operation executed at startup only.

## Proposed Solution
### Configuration Loader
- Modify `load_model_specs_from_env` to read only `MODEL_<KEY>_UPSTREAM_MODEL`, compute `alias` via helper `derive_alias(upstream_model)`, and raise errors when the upstream variable is missing.
- Introduce `derive_alias` in `config.py` (and share with CLI if needed) to:
  - Strip `openai/` or other known provider prefixes based on the `MODEL_CAPS` table or string patterns.
  - Return the upstream model untouched when no slash-delimited provider prefix exists.
- When `MODEL_<KEY>_ALIAS` is detected, raise a `ValueError` instructing operators to remove the legacy variable.

### CLI & Dataclass Updates
- Update `parse_model_spec` to treat `alias` as optional. If absent, call `derive_alias` on the provided upstream value.
- Adjust `ModelSpec.__post_init__` to allow alias injection after initialization, or compute alias before instantiating the dataclass.
- Ensure CLI help text (`--model-spec`) documents the default alias behavior and clarifies that environment aliases are no longer supported.

### Entrypoint & Legacy Scripts
- Update `entrypoint.sh` (and any similar boot scripts) to call `add_model` with derived aliases using the same helper logic, failing the build/startup when legacy alias variables are provided.
- Provide automated tests for the shell path via existing pytest harness to confirm alias derivation logic is mirrored.

### Documentation & Migration
- Rewrite relevant sections of `README.md` and `.env.example` to remove alias variables, replacing snippets with single-source upstream examples.
- Call out the breaking change prominently in the docs release notes to guide operators through the update.
- Update prior PRDs or references (if necessary) to reflect the new schema so upcoming features align with the simplified contract.

### Telemetry & Logging
- Verify telemetry continues to use `ModelSpec.alias` so downstream logs reflect the normalized alias; add coverage ensuring alias/upstream combinations in logs remain consistent.

## Testing Strategy (TDD)
- Author failing unit tests before implementation:
  - `tests/unit/test_config.py`: new cases for alias derivation, error handling when legacy alias env vars appear, and CLI defaults.
  - `tests/unit/test_config_coverage.py`: adjust fixtures to drop alias variables and add coverage for the failure path when aliases are provided.
  - `tests/unit/test_entrypoint_sh.py`: ensure generated YAML uses normalized aliases when only upstream variables are declared and that startup fails with legacy alias variables.
- Extend integration tests:
  - `tests/integration/test_multi_model_integration.py`: remove alias env vars from fixtures and assert resulting config surface matches expectations.
  - `tests/integration/test_reasoning_integration.py`: confirm reasoning behavior unaffected when aliases auto-derive.
- Update telemetry tests if they assert explicit alias strings to reflect the new derivation.
- Run `_flake8.ps1` (or equivalent fallback) and `pytest --cov` once tests pass, ensuring overall coverage stays above 95%.

## Milestones
1. **Design & Test Authoring** (0.5 day): add new test cases capturing alias derivation and hard failures when legacy alias variables are present.
2. **Implementation** (1 day): update config loader, CLI parser, entrypoint scripts, and utility helpers; ensure failure paths and normalization logic match tests.
3. **Docs & Cleanup** (0.5 day): update README, `.env.example`, release notes, and verify lint/test pipelines clean.

## Acceptance Criteria
- Starting the proxy with only `MODEL_PRIMARY_UPSTREAM_MODEL=gpt-5` produces a config exposing alias `gpt-5` and upstream `openai/gpt-5` without errors.
- Multi-model env (`MODEL_GPT5_UPSTREAM_MODEL`, `MODEL_DEEPSEEK_UPSTREAM_MODEL`) renders YAML with aliases `gpt-5` and `deepseek-v3.2` respectively, sans alias env vars.
- Providing any `MODEL_*_ALIAS` environment variable causes startup to fail with a clear remediation message.
- CLI invocation `--model-spec key=gpt5,upstream=openai/gpt-5` yields alias `gpt-5`; specifying `alias=custom` still works.
- Updated docs reflect new schema, and sample `.env` files run without alias variables.
- Test suite passes with ≥95% coverage, and linting reports no new violations.

## TODO (TDD Checklist)
- [ ] Add unit tests verifying alias derivation from upstream models, including prefixed values.
- [ ] Add regression tests ensuring startup fails cleanly when legacy alias env vars are present.
- [ ] Update integration tests to operate without `MODEL_*_ALIAS` variables.
- [ ] Implement configuration, CLI, and entrypoint changes to satisfy the new tests.
- [ ] Refresh documentation and examples to remove alias variables.
- [ ] Rerun `_flake8.ps1` (with fallback command if unavailable) and `pytest --cov` to confirm clean lint status and ≥95% coverage before shipping.
