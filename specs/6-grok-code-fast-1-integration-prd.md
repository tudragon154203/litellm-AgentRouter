# Grok Code Fast-1 Integration PRD

## Overview
- Existing support is limited to `demo/grok/test_grok_code_fast_1.py`, which hardcodes credentials and bypasses proxy configuration, preventing production use.
- Objective: promote Grok Code Fast-1 to a first-class model within the LiteLLM proxy + CLI stack so operators can route traffic through standard configuration, logging, and observability paths.
- MVP focuses on parity with other OpenAI-compatible models (completion, reasoning, streaming) while obeying security requirements (no embedded keys) and keeping proxy behaviour consistent.
- Out of scope: UI surfacing, adaptive routing, or automatic key rotation; these can follow once the proxy path is stable.

## User Stories
- *Platform engineer* wants to advertise Grok Code Fast-1 alongside existing models without bespoke scripts so customer traffic can be switched using the shared configuration file.
- *Security officer* needs secrets supplied through environment variables or vault-backed configuration, not committed to source control, to comply with key management policy.
- *QA analyst* requires automated tests proving Grok requests succeed—streaming and non-streaming—before certifying the model for preview tenants.
- *Support engineer* needs actionable logging/metrics whenever Grok-specific fallbacks (e.g., dropped params) occur to debug customer incidents quickly.

## Functional Requirements
- Add Grok Code Fast-1 model definition to proxy configuration (likely `ModelSpec`) exposing a public alias (e.g., `grok-code-fast-1`) that maps to upstream `openai/grok-code-fast-1`.
- Extend configuration loader to recognize Grok-specific base URL + API key env variables (`GROK_BASE_URL`, `GROK_API_KEY`) with documented precedence rules (model-specific > global).
- Ensure `litellm.drop_params = True` toggle is applied via configuration rather than demo script so Grok requests safely omit unsupported parameters.
- Guarantee both synchronous completion and streaming APIs function, including reasoning-oriented payloads that Grok accepts; capability flags must reflect real support.
- Integrate Grok into CLI command discovery (e.g., `cli.py` or `proxy.py`) so operators can list/launch it with existing flags.
- Replace demo hard-coded key with documented instructions to rely on env vars; keep demo runnable by reading from env and failing fast with actionable errors if missing.
- Add documentation anchors (README or docs/) pointing to setup steps, expected environment configuration, and limitations.

## Non-Functional Requirements
- Maintain 95%+ test coverage; new code paths need instrumentation or targeted tests to avoid regressions.
- Preserve existing latency/throughput expectations; introducing Grok must not degrade proxy startup or request dispatch materially (target: <5% regression in comparable benchmarks).
- Ensure logging aligns with current verbosity controls, adding Grok-specific messages only at debug/info levels already in use.
- Protect sensitive information: never emit API keys in logs or tracebacks; mask tokens similarly to other providers.

## Edge Cases
- Missing or malformed Grok credentials → proxy should refuse to start the Grok model, emit clear error, and continue serving other models.
- Requests containing unsupported parameters (e.g., `reasoning`, `response_format`) should drop or transform gracefully without breaking for other providers.
- Streaming responses that end abruptly or provide empty deltas should still resolve generators cleanly and surface warnings rather than stack traces.
- Fallback when Grok returns non-JSON error body; ensure error handler surfaces status code + sanitized text.
- Concurrent requests across Grok and other models must not share mutable configuration (e.g., headers dict) to avoid cross-provider leakage.

## TDD & Testing Plan
- Start by running `_flake8.ps1` to capture baseline lint status before any edits, per repo policy.
- Author new failing unit tests first:
  - Config parser test ensuring Grok model appears with correct alias, base URL, key env resolution, and `drop_params` flag (`tests/config` or similar).
  - CLI/proxy integration test mocking LiteLLM completion to confirm Grok provider is registered and invoked with headers + retries expected.
  - Streaming test validating generator behaviour (collect chunks, ensure final usage payload) using a stubbed LiteLLM response.
  - Security regression test asserting no hard-coded keys remain and environment validation raises explicit errors when unset.
- Execute the new tests (expect failures), implement minimal code to satisfy them, rerun to ensure they pass, then run relevant existing suites to confirm no regressions.
- After changes, rerun `_flake8.ps1`; if lint violations occur, execute `_autopep8.ps1`, apply residual fixes, and rerun `_flake8.ps1` until clean.
- Update or create coverage report to verify ≥95% overall; if coverage dips, backfill targeted tests before shipping.

## Verification Steps
- `_flake8.ps1` → expect clean baseline; record timestamp/outcome.
- `pytest` (or targeted test command) → run new Grok suites first, confirm prior failures now pass.
- `pytest --maxfail=1 --cov` (or project-standard coverage invocation) → confirm global coverage threshold maintained.
- Manual smoke: launch proxy with Grok config in a dry-run environment, perform one sync + streaming request using mock/stub credentials, observe logging/metrics.
- Documentation build or lint (if applicable) to ensure new instructions compile/render.

## Assumptions
- Grok endpoint remains OpenAI-compatible (same schema as test script) so existing LiteLLM wrappers suffice with minimal overrides.
- LiteLLM already supports `custom_llm_provider="openai"` path required by Grok; no upstream patching is needed.
- Operators can provision Grok credentials externally; secret injection pipeline already exists for other models.
- Demo script will stay as a developer aid but must align with shared configuration once integration lands.

## Follow-Up
- Evaluate automated health checks (periodic ping) for Grok once basic integration stabilizes.
- Add load/performance benchmarks comparing Grok with other models to inform routing decisions.
- Explore consolidating provider-specific header logic to reduce duplication introduced by Grok support.
- Consider feature-toggling Grok availability per environment (e.g., staging vs. production) once customer demand clarifies.

