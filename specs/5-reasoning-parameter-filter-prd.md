# Reasoning Parameter Filter PRD

## Overview
- Current proxy forwards OpenAI-style payloads upstream; upstream rejects unknown `reasoning` parameter, blocking requests.
- MVP requirement: detect `reasoning` when preparing/forwarding payload, omit it, ensure no regressions to other parameters, keep auth/logging untouched.
- Out of scope: broader schema validation, mutation of other optional params, upstream capability negotiation, CLI changes, UI exposure.

## User Stories
- *Integrations developer* needs existing automations (now including `reasoning`) to keep working without manual edits, so requests stop failing.
- *Reliability engineer* wants observable metrics/verbosity proving the proxy dropped `reasoning` to avoid silent data loss triage.
- *QA engineer* needs coverage demonstrating payloads with/without `reasoning` reach upstream unchanged otherwise.

## Functional Requirements
- When proxy builds request for upstream, strip `reasoning` key at the outermost payload level for both `/v1/chat/completions` and `/v1/responses`, as well as the legacy aliases `/chat/completions` and `/responses`; tolerate any truthy/falsy value types.
- Keep nested `reasoning` fields inside other objects unchanged; only top-level parameter is targeted.
- Preserve request ordering/body formatting otherwise; no mutation of headers or retries.
- Emit debug-level log entry when drop occurs; message includes request identifier but no PII.
- Ensure behaviour compatible with both sync and streamed responses.

## Edge Cases
- Parameter absent → forward untouched without log emission.
- Parameter present but `None` / empty → still drop and log.
- Additional unknown keys alongside `reasoning` → leave them untouched.
- Batched/multi-message payloads where `reasoning` appears per item → clarify whether spec applies (assumption: only top-level removal needed; follow-up if batches introduced).
- `/v1/responses` requests mirror chat completions semantics and must receive identical filtering/logging rules; legacy `/chat/completions` and `/responses` aliases also require the same treatment.

## TDD & Testing Plan
- Add unit test (fail first) for request builder ensuring payloads targeting `/v1/chat/completions`, `/chat/completions`, `/v1/responses`, and `/responses` miss `reasoning` before hitting HTTP layer.
- Add integration-style test with mocked upstream verifying request body matches expected sans `reasoning` for both endpoint families.
- Add regression test proving nested `{"metadata": {"reasoning": ...}}` survives untouched.
- Extend logging test to assert debug message emitted exactly once per dropped parameter.
- Confirm coverage ≥95%; expand test harness if new path lowers coverage (track with coverage report).

## Verification Steps
- Run `_flake8.ps1` prior to changes; expect current status clean.
- After implementing tests & behaviour, ensure failing tests turn green in order: new unit test, integration test, logging test.
- Re-run `_flake8.ps1`; if issues, execute `_autopep8.ps1`, resolve leftovers, rerun to confirm clean.

## Assumptions
- Proxy code already centralizes payload preparation at a single interception point.
- Dropping `reasoning` has no contractual impact on clients relying on confirmation echoes.
- Debug logging acceptable overhead; no new log levels required.
- `/v1/responses` endpoint is available in proxy routing stack (with `/responses` alias) and should leverage the same interception point as chat completions (including `/chat/completions` alias).

## Follow-Up
- Revisit batching/multi-tenant payload handling once encountered.
- Consider formal upstream capability negotiation to auto-resolve future unknown parameters.
