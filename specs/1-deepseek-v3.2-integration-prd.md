# DeepSeek v3.2 Integration PRD

## Background
- LiteLLM Local Gateway currently ships with defaults and docs tuned for AgentRouter's GPT-5 model.
- The CLI generates a LiteLLM config on-the-fly that always prefixes `openai/` to the upstream model and exposes it under a single alias.
- A demo script (`demo/deepseek/test_v3.2.py`) proves DeepSeek v3.2 already works via the upstream AgentRouter endpoint when launched manually.
- Product goal: first-class support for selecting `deepseek-v3.2` so the gateway can expose either GPT-5 or DeepSeek v3.2 (and later additional models) without ad-hoc scripts.

## Goals
- Support running the proxy with both GPT-5 and DeepSeek v3.2 concurrently so downstream clients can target either alias without restarting the service.
- Allow operators to configure DeepSeek v3.2 via the unified CLI/environment schema without touching LiteLLM YAML manually.
- Ensure generated LiteLLM config routes to the correct upstream model while keeping GPT-5 defaults available when desired.
- Document setup so users know how to run the gateway with either model and understand any parameter differences (e.g., recommended reasoning defaults).
- Add automated coverage that verifies config generation for multi-model deployments and new model options.

## Non-Goals
- No changes to the underlying LiteLLM library beyond configuration generation.
- No UI/UX beyond CLI + docs.
- No dynamic multi-model routing; still one alias per proxy process.
- No direct integration of the standalone demo script into the product code.

## Users & Scenarios
- **Operator switching models**: wants to run the proxy against DeepSeek for specific workloads without editing YAML by hand.
- **CI/QA engineer**: needs regression tests confirming config generation for both GPT-5 and DeepSeek after future refactors.
- **Doc consumer**: wants a concise recipe to run DeepSeek via docker-compose or local CLI.

## Functional Requirements
1. CLI accepts multiple `--model-spec` inputs (e.g., `--model-spec upstream=gpt-5` and `--model-spec upstream=deepseek-v3.2`) and/or honors a new `.env` driven list so the generated config contains two `model_list` entries.
2. Environment configuration supports declaring at least two models concurrently via indexed keys (e.g., `PROXY_MODEL_KEYS=gpt5,deepseek` paired with `MODEL_GPT5_UPSTREAM_MODEL`, `MODEL_DEEPSEEK_UPSTREAM_MODEL`, etc.), deriving aliases from the upstream identifiers automatically.
3. When `--alias` is not provided, defaults remain the upstream identifier (e.g., `gpt-5`); docs should clarify recommended naming (e.g., `deepseek-v3.2`) and how default alias interacts with multi-model configs.
4. Generated config must reflect per-model `reasoning_effort` settings, treating the value `none` as an instruction to omit the field.
5. Default `drop_params` remains enabled globally (hard-coded true); no per-model override required.
6. Proxy startup logs clearly display all configured aliases and upstream models.
7. Unit tests cover config output for GPT-5 only, DeepSeek only, and dual-model scenarios, including reasoning effort handling.
8. Integration test (smoke) ensures CLI `--print-config` with multi-model env produces expected YAML ordering.
9. README updated with DeepSeek instructions, environment variable redesign, and dual-model usage examples.
10. Provide sample `.env.multi-model.example` (or expand `.env.example`) illustrating dual-model configuration.

## Non-Functional Requirements
- Keep config generation deterministic and minimal—no provider-specific branches outside well-scoped helpers.
- Avoid leaking API keys in logs; follow existing patterns from demo (masking if needed).
- Tests should remain fast and not call live upstream endpoints.

## Proposed Solution
### CLI & Config Layer
- Introduce a `ModelSpec` dataclass wrapping alias, upstream model id, base URL, API key env, and optional reasoning effort.
- Parse model specs from both CLI (`--model-spec alias=...,upstream=...,base=...,key_env=...,reasoning=...`) and environment (iterating `PROXY_MODEL_KEYS` list to load `MODEL_<KEY>_*` variables). Default behavior consumes the multi-model schema even when only one key is supplied.
- Extend `config.render_config` (or introduce `render_model_list`) to iterate through provided `ModelSpec` instances and append one `model_list` entry per spec.
- Maintain capability mapping for explicit overrides when a provider cannot accept `reasoning_effort`, while keeping the default assumption that models (including DeepSeek v3.2) support the field.
- Continue prefixing with `openai/` as demo confirmed compatibility with AgentRouter upstream. Consider abstraction for future non-OpenAI-compatible providers but out-of-scope to implement now.
- Update `main` startup log to include the list of configured aliases and their upstream targets for clarity.

#### Environment Variable Redesign
- Introduce `PROXY_MODEL_KEYS` (comma-separated identifiers) to declare active models; each identifier maps to namespaced variables (`MODEL_<KEY>_UPSTREAM_MODEL`, optional `MODEL_<KEY>_REASONING_EFFORT`), with aliases derived automatically.
- Support `OPENAI_BASE_URL` and `OPENAI_API_KEY` global fallbacks when per-model values are omitted.
- Drop legacy single-model environment variables; require multi-model schema even for one-model deployments (with docs highlighting minimal single-entry example).

### Documentation
- Add DeepSeek usage section in README with CLI and docker-compose examples (`PROXY_MODEL_KEYS=gpt5,deepseek` plus corresponding `MODEL_*` variables using global defaults).
- Call out recommended reasoning values for each provider and confirm `drop_params` recommendation.
- Provide migration notes for removing legacy single-model environment variables.
- Reference demo script for advanced streaming example (optional).

### Testing
- Unit tests:
  - Update `tests/unit/test_cli.py` to drop coverage of retired single-model env vars and add cases for `PROXY_MODEL_KEYS`, per-model alias/upstream parsing, and global `OPENAI_BASE_URL`/`OPENAI_API_KEY` defaults.
  - Extend config rendering tests to assert that:
    - GPT-5 spec inherits API base/key from globals while retaining reasoning effort.
    - DeepSeek spec omits reasoning effort unless explicitly set to `none`.
    - Dual-model environment (`PROXY_MODEL_KEYS=gpt5,deepseek`) yields two entries with correct upstream prefixes.
  - Add unit coverage for environment loader ensuring it resolves `MODEL_<KEY>_*` values and raises helpful errors when required fields missing.
- Integration tests:
  - New fixture `.env` exercising dual-model configuration; run `python -m src.main --print-config` and snapshot YAML.
  - Minimal single-model path (`PROXY_MODEL_KEYS=primary`) verified similarly.
- Ensure regression tests run under CI without network calls.

### Tooling & Dev Experience
- No dependency changes expected.
- Confirm `docker-compose` inherits `PROXY_MODEL_KEYS` and associated `MODEL_*` variables (plus global defaults) from `.env` so switching models only requires env file edits.

## Milestones
1. **Implementation** (1–2 days)
   - Add capability mapping + reasoning guard.
   - Update logging and README.
   - Refresh `.env.example` with dual-model schema; include minimal single-entry example using new variables.
2. **Testing** (0.5 day)
   - Write/expand unit & integration tests.
3. **Documentation & Review** (0.5 day)
   - Finalize README updates, ensure demo references consistent.

## Acceptance Criteria
- Running `python -m src.main --print-config` with a dual-model `.env` (`PROXY_MODEL_KEYS=gpt5,deepseek`, etc.) emits YAML containing both aliases, with GPT-5 and DeepSeek carrying their configured reasoning levels (omitting the field only when set to `none`).
- Minimal single-model `.env` using `PROXY_MODEL_KEYS=primary` (with the new schema) renders correct config without relying on deprecated variables.
- Tests pass locally and in CI.
- README documents dual-model configuration and migration notes.
- Startup logs list all configured aliases and upstream models.
- Test suite maintains >95% coverage and linting passes with zero errors.
