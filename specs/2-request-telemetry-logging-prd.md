# Request Telemetry Logging PRD

## Background
- LiteLLM launcher currently relies on the default Uvicorn access log from `litellm.proxy` which only surfaces client IP, HTTP verb, and status (e.g., `INFO:     172.27.0.1:52424 - "POST /v1/chat/completions HTTP/1.1" 200 OK`).
- Operators and developers lack visibility into which downstream model aliases are being exercised, how many tokens are consumed, or how long reasoning-heavy calls take.
- Troubleshooting customer reports, capacity planning, and cost attribution all require richer telemetry per request, especially as the launcher now supports multiple model aliases (`src/config.py`) and reasoning features.

## Goals
- Emit structured request-level telemetry for every `POST /v1/chat/completions` call covering model selection, token usage (prompt, completion, reasoning), and end-to-end latency.
- Provide parity for both streaming and non-streaming chat completions so operators always get a terminal status record.
- Document the new behavior so observability tooling (CloudWatch, Loki, etc.) can parse the emitted logs easily.

## Non-Goals
- No centralized metrics backend or dashboard work (Grafana, Datadog, etc.).
- No request body redaction features beyond omitting prompt/content payloads.
- No automatic alerting or rate limiting tied to the new telemetry.
- No changes to LiteLLM core package; the launcher layers the instrumentation externally.

## Users & Scenarios
- **On-call engineer**: correlates latency spikes with specific model aliases and token usage patterns.
- **Cost analyst**: exports logs to compute per-model input/output token totals for billing reconciliation.
- **Developer debugging reasoning**: checks whether reasoning tokens dominate completion tokens for a given request.
- **Support engineer**: inspects failed requests to understand error types, durations, and model context without rerunning reproduction steps.

## Functional Requirements
1. Log exactly one structured event (JSON object string) per `POST /v1/chat/completions` request after the response stream completes or fails.
2. Captured fields (nullable when data unavailable):
   - `event`: fixed string `chat_completion`.
   - `timestamp`: ISO-8601 with timezone.
   - `remote_addr`: best-effort client IP from FastAPI request.
   - `path`: literal `/v1/chat/completions`.
   - `method`: `POST`.
   - `status_code`: final HTTP status.
   - `duration_ms`: float milliseconds between request start and final byte sent.
   - `streaming`: boolean derived from request payload (`stream`) or response type.
   - `request_id`: completion response `id` when present.
   - `model_alias`: value from request (`model`) after alias resolution.
   - `upstream_model`: resolved upstream model (`openai/...`) using the active `ModelSpec`.
   - `prompt_tokens`: usage prompt count (integer) when returned.
   - `completion_tokens`: output token count excluding reasoning.
   - `reasoning_tokens`: reasoning token count when provider returns it.
   - `total_tokens`: total usage reported.
   - `error_type`: high-level error name (e.g., `RateLimitError`) on failure, else `null`.
   - `error_message`: short sanitized message (no API keys) on failure, else `null`.
3. Middleware must handle both JSON responses and streaming generators; the log entry is emitted only after the final chunk / generator exhaustion to ensure accurate duration and token totals.
4. For requests without usage metadata (provider omission or failure), log token fields as `null` and add `missing_usage=true` flag.
5. Ensure alias→upstream resolution uses the final config produced in `src/config.py` so logs reflect generated LiteLLM routing (including implicit `openai/` prefix).
6. Propagate `X-Request-ID` (if provided) into the log payload as `client_request_id` to aid correlation.
7. Avoid logging message content, API keys, or other sensitive payload fields.
8. Provide README documentation describing emitted fields and a sample log entry.

## Non-Functional Requirements
- Added middleware must keep overhead <5 ms per request under typical load (no blocking I/O).
- Implementation must be thread- and worker-safe when `--num_workers` > 1.
- Logging must never raise exceptions that break responses; failures should be caught and downgraded to a warning.
- All new code follows existing style guidelines and includes targeted unit coverage.

## Proposed Solution
### Instrumentation Strategy
- Introduce `src/telemetry.py` with helpers to register a FastAPI middleware against `litellm.proxy.proxy_server.app`.
- In `src/proxy.py`, before invoking `run_server.main`, import the new telemetry module and call `instrument_proxy_logging(model_specs=args.model_specs)` once per process.
- Middleware intercepts the request, records `time.perf_counter()`, reads minimal metadata (model alias, streaming flag, headers), and wraps the response object to hook `send` events. For non-streaming responses the wrapper buffers the final body bytes; for streaming it decorates the generator to watch the terminal chunk (LiteLLM sends usage in the final SSE delta).

### Data Extraction
- Use the `ModelSpec` list already attached to `args` (`src/config.py`) to build an alias→upstream lookup table. Default to the alias itself when resolution fails.
- Parse response bodies with `json.loads` when the MIME type is JSON; extract usage from `response["usage"]` and, if available, `response["usage"]["output_token_details"]["reasoning_tokens"]`.
- For streaming responses, sniff SSE events for a final message containing `"usage"`; accumulate the last JSON fragment to parse once streaming concludes.
- When the response is an error (HTTP ≥400 or an exception raised during handling), capture the exception type/message and emit the log with `status_code` and `error_*` fields populated.

### Logging Format
- Emit a single line via the standard `logging` module using a `Logger` named `litellm_launcher.telemetry`.
- Serialize the payload with `json.dumps`, ensuring floats/ints remain native types.
- Configure the logger with `INFO` level by default; operators can override via standard Python logging configuration if desired.

### Failure Handling
- Wrap all parsing logic in `try/except`; on failure, log a secondary warning (`telemetry.parse_failure`) but still emit a telemetry event with `parse_error=true`.
- Ensure the middleware re-raises original exceptions after logging so HTTP semantics remain unchanged.

## Testing
- Unit tests using FastAPI's `TestClient` with stub handlers to assert log emission for:
  - Successful non-streaming completion with usage payload.
  - Streaming completion where usage arrives on the terminal chunk.
  - Provider omission of usage data (verifies `missing_usage` flag).
  - HTTP error path ensuring `error_type`/`error_message` populate and no token fields.
- Tests validating alias→upstream resolution from `ModelSpec`.

## Tooling & Dev Experience
- Update `README.md` with a new "Request Telemetry Logging" section showing example output and explaining default behavior.
- Provide a sample log snippet in `specs` or docs to aid observability teams.
- No additional external dependencies; rely on Python stdlib.

## Milestones
1. **Implementation** (1 day): add telemetry module, integrate with proxy startup, ensure middleware registered by default.
2. **Testing** (0.5 day): unit tests for non/streaming cases and error handling.
3. **Documentation & Review** (0.5 day): README updates, changelog entry, code review.

## Acceptance Criteria
- Launching the proxy locally (`python -m src.main ...`) and issuing a chat completion produces an INFO log line with the specified fields and accurate duration/token counts.
- Streaming completions emit exactly one log entry after the final chunk with `streaming=true` and populated usage.
- Failed requests emit telemetry entries capturing `error_type`, `error_message`, and `status_code`.
- Test suite passes (`pytest`) and new tests cover success, streaming, missing usage, and error scenarios.
