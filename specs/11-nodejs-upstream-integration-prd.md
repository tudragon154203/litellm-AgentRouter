# Node.js Upstream Proxy

**Status**: Proposed  
**Priority**: High  
**Complexity**: High

## Problem Statement

- The current launcher relies on LiteLLM's Python OpenAI provider to call the upstream `agentrouter.org` endpoint, but the Python client is now blocked and the proxy can no longer reach the upstream server.
- A working workaround already exists in `demo/nodejs/qwen_code_openai_working_nodejs.py`, which demonstrates that the same upstream can be reached from the Node.js OpenAI client. We therefore need to replace the Python upstream plumbing with a Node.js component while keeping the existing OpenAI-compatible surface untouched.
- The migration must remain manageable within the current modular architecture (`src/config/`, `src/main.py`, `src/proxy.py`, `src/utils.py`, `src/telemetry/`) and must not regress telemetry, configuration, or coverage guarantees.

## Testing & Acceptance Criteria

1. **Node unit tests**: Implement `node --test` (or `vitest/jest`) suites that exercise the new Node HTTP proxy logic, covering
   * request forwarding from `/v1/chat/completions` and `/v1/completions` to the `openai` client,
   * header population (including the canonical QwenCode user agent),
   * error paths (client failures, upstream 4xx/5xx, timeouts),
   * configurable timeouts/ports via environment variables.
   These tests should fail until the proxy logic is implemented and pass once Node request handling is wired up.

2. **Python unit tests**: Extend `tests/unit/` to assert that
   * the runtime configuration respects new Node upstream flags (e.g., `NODE_UPSTREAM_PROXY_ENABLE`),
   * the entrypoint starts the Node helper process (mocking `subprocess.Popen`) and that resources are cleaned up on shutdown,
   * the generated LiteLLM config points at the Node proxy base URL when the feature flag is enabled.
   These tests should run before touching implementation to capture regressions early, and they must preserve the current >95% coverage target.

3. **Integration tests**: Add coverage under `tests/integration/` that
   * spins up the Node helper (in-process or via subprocess) and the LiteLLM proxy, and
   * issues a chat completion via the full stack to confirm Node is forwarding to the real upstream (or a mocked equivalent) and that telemetry logs/response shapes remain OpenAI-compatible.
   Ensure these tests routinely use `pytest` and respect existing integration runners, skipping gracefully if Node is missing.

4. **Linting & formatting**: Before final handoff run `_flake8.ps1`, fix any violations via `_autopep8.ps1` plus manual adjustments, and rerun `_flake8.ps1` to confirm the tree is clean.

## Proposed Solution

- **Node helper service**: Create a lightweight Node.js HTTP service (e.g., `node/upstream-proxy.mjs`) that listens on port `4000`. It exposes at least the `/v1/chat/completions` and `/v1/completions` endpoints, parses incoming bodies, and reuses the official `openai` Node client to call the real upstream base (`OPENAI_BASE_URL`, default `https://agentrouter.org/v1`). Responses (including headers and status codes) are streamed straight back to the Python proxy.
- **Process supervision**: Update `src/config/entrypoint.py` (or a dedicated helper under `src/node`) to spawn this Node service before generating the LiteLLM config. The helper should inject `NODE_USER_AGENT` (derived from `utils.build_user_agent`) into the Node env, then ensure the subprocess is terminated when the proxy shuts down.
- **Configuration handoff**: When `NODE_UPSTREAM_PROXY_ENABLE` is true, override the generated LiteLLM `api_base` to point at `http://127.0.0.1:4000` (or `http://node-proxy:4000` in docker-compose) so Litellm routes through Node. Preserve the existing `OPENAI_BASE_URL` for other code paths, logging the substitution for debugging. Ensure `src/config/config.py` surfaces the new values and that `validate_prereqs()` inspects both Python and Node prerequisites (e.g., `node --version`).
- **Docker/compose updates**: Extend `Dockerfile` to install a Node.js runtime (`node`, `npm ci`), copy the `package.json`/`package-lock.json`, and run the helper alongside the Python entrypoint. Update `docker-compose.yml`/`entrypoint.sh` so the Node service comes up before `python -m src.config.entrypoint`. Mount the new Node files for local dev and ensure volume overrides remain consistent.
- **Telemetry/logging discipline**: Keep the existing structured telemetry middleware intact. The Node helper should emit structured JSON lines (e.g., `{ "node_proxy": {...} }`) so logs can be correlated; the Python telemetry middleware should capture the `x-request-id` if we forward it.

## Architecture

1. `entrypoint.sh` → `python -m src.config.entrypoint`.
2. Entry point spawns Node helper: preserves `OPENAI_BASE_URL`, ensuring the helper logs the upstream base for debugging.
3. LiteLLM config generator uses Node base (`http://127.0.0.1:4000/v1` or `http://node-proxy:4000/v1`) when the proxy flag is enabled; `custom_llm_provider: openai` remains unchanged.
4. LiteLLM proxy (`litellm.proxy`) talks to Node helper, which calls Node `openai` client, which then talks to `agentrouter.org`.
5. Node helper streams responses back so Python telemetry sees the original upstream latency/headers.

## Configuration & Runtime

- **New environment variables**:
  - `NODE_UPSTREAM_PROXY_ENABLE` (bool flag, defaults to `true` in production) – whether to route LiteLLM through Node.
- All configuration values funnel through `src.config.config.runtime_config` so tests and CLI flags can override them (`--upstream-base`, etc.).
- The Node helper reads `NODE_USER_AGENT` to keep the existing QwenCode UA string and logs the `OPENAI_BASE_URL`.
- The Node helper always listens on port `4000` to match the LiteLLM proxy port convention.

## Rollout & Migration

1. Prototype the Node helper in `node/upstream-proxy.mjs` and add Node tests; these should fail initially (TDD).
2. Extend Python config/entrypoint code to consume the helper (ensuring `runtime_config` loads new env variables) and update unit tests accordingly.
3. Update Dockerfile and docker-compose to install Node, copy the helper, and supervise it during container startup.
4. Once tests pass (`npm test`, `pytest`, `_flake8.ps1`), merge the change and monitor logs for Node helper readiness.
5. If Node fails (missing binary or helper crash) the entrypoint should emit a clear error and exit with a non-zero code to prevent silent degradation.

## Follow-up & Verification Steps

- Run `_flake8.ps1` first; if it fails, run `_autopep8.ps1`, fix remaining issues manually, and rerun `_flake8.ps1`.
- Run `npm test` (or `node --test`) to validate the Node helper followed by `pytest` to keep coverage above 95%.
- Review `htmlcov/index.html` to ensure the new Python tests are covered and that no untested paths regressed.
- Document the new Node helper in README and `specs/` (this PRD can serve as the authoritative reference).
- Update telemetry dashboards/alerting to surface Node helper failures if needed.

## Assumptions & Risks

- Node.js is available in the deployment environment; an updated Docker image or `apt` install is acceptable.
- The Node helper can faithfully reproduce the OpenAI-compatible API surface with deterministic latency.
- Any future upstream extensions (embeddings, moderation, audio) will be handled by extending the Node helper rather than the Python stack.
