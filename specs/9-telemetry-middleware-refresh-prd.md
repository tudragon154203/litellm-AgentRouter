# PRD: Telemetry Middleware Refresh

## 1. Context
Telemetry logging was previously implemented as a single, tightly coupled middleware class that relied on implicit environment toggles and global state. The redesign removes backward compatibility expectations, enabling a clean architecture that favors explicit dependency injection, SOLID boundaries, and future extensibility.

## 2. Goals
- Provide a modular telemetry middleware package with separable concerns (configuration, request context extraction, usage parsing, event publication, sinks).
- Require host applications to inject dependencies explicitly (no hidden env-based behavior).
- Support both standard JSON and streaming response telemetry with replayable streams.
- Enable multiple telemetry sinks and simple customization (e.g., console logging, in-memory capture, structured logger).
- Deliver ≥95% code coverage via dedicated unit tests.

## 3. Non-Goals
- Maintaining legacy middleware API or environment variable semantics.
- Implementing asynchronous/offline sink processing.
- Persisting telemetry beyond in-memory/logging sinks.
- Backfilling historical telemetry data.

## 4. Personas & Use Cases
- **Platform Engineer**: Configures middleware with a custom sink that forwards telemetry to observability stack.
- **Developer**: Adds new usage extractor or reasoning filter without altering middleware core.
- **QA/Test Engineer**: Captures emitted telemetry events in tests via in-memory sink to assert correct behavior.

## 5. Requirements

### Functional
1. New package `src/middleware/telemetry/` exposes `TelemetryMiddleware` requiring configuration and pipeline dependencies at construction.
2. `TelemetryMiddleware` must short-circuit when toggle returns false before invoking downstream call.
3. Request reasoning filtering is handled by dedicated policy object; it can mutate request body and produce debug metadata.
4. Usage extraction supports both JSON bodies and streaming iterators; streaming paths must replay consumed chunks.
5. Pipelines emit domain events (`RequestReceived`, `ResponseCompleted`, `ErrorRaised`) to one or more sinks implementing a common interface.
6. Alias resolution and telemetry enablement are supplied by injected strategies; no implicit environment lookups.
7. Middleware callers can choose from built-in sinks (structured logger, console, in-memory test sink).

### Non-Functional
1. Package must achieve ≥95% unit test coverage with new tests under `tests/`.
2. Code must satisfy `_flake8.ps1` linting; apply `_autopep8.ps1` only if needed.
3. Components should avoid global state; favor immutable data structures and pure functions where practical.

## 6. Success Metrics
- 100% new tests covering main request/response/error flows pass.
- Coverage report shows project-wide coverage ≥95% after changes.
- Manual smoke test via FastAPI app demonstrates telemetry events being emitted through logger sink.

## 7. Milestones
1. Publish architecture note (`docs/telemetry/REFRESH.md`) and finalize interface contracts.
2. Author failing unit tests for middleware, pipeline, reasoning filter, usage extractors, and sinks.
3. Implement new telemetry package; remove legacy `src/middleware/telemetry.py`.
4. Update application wiring + docs; ensure tests and lint pass.

## 8. Dependencies
- Existing FastAPI/Starlette middleware infrastructure.
- Logger configuration for default sink behavior.
- Python async iteration semantics for streaming responses.

## 8a. Planned Module Structure
- `src/middleware/telemetry/__init__.py`: public exports (`TelemetryMiddleware`, config types).
- `src/middleware/telemetry/config.py`: `TelemetryConfig`, toggle and alias strategy interfaces.
- `src/middleware/telemetry/middleware.py`: Starlette middleware implementation.
- `src/middleware/telemetry/request_context.py`: request parsing and reasoning filter policies.
- `src/middleware/telemetry/usage.py`: usage extraction strategies, streaming helpers.
- `src/middleware/telemetry/pipeline.py`: event orchestration and sink fan-out.
- `src/middleware/telemetry/events.py`: event and token dataclasses.
- `src/middleware/telemetry/sinks/console.py`: console sink implementation.
- `src/middleware/telemetry/sinks/logger.py`: structured logger sink implementation.
- `src/middleware/telemetry/sinks/inmemory.py`: testing sink for assertions.

## 9. Risks & Mitigations
- **Risk**: Streaming responses not replayed correctly.  
  **Mitigation**: Add dedicated tests with async generators verifying replayable iterators.
- **Risk**: Host applications forget to inject required dependencies.  
  **Mitigation**: Constructor enforces explicit arguments and type hints; docs provide wiring examples.
- **Risk**: Coverage dip due to new modules.  
  **Mitigation**: Expand unit tests and instrumentation to cover error paths.

## 10. Open Questions
1. Should telemetry sinks support batching/backpressure?
2. Do we need sampling configuration built into the toggle interface?
3. Should we expose telemetry events via Pydantic models for schema validation?

## 11. TODO Checklist
- [ ] Finalize interface definitions for config, pipeline, usage extractors, and sinks.
- [ ] Draft API examples for host application wiring.
- [ ] Author unit test plan and scaffolding under `tests/unit/middleware/telemetry/`.
- [ ] Implement telemetry package modules following planned structure.
- [ ] Remove legacy `src/middleware/telemetry.py` and adjust imports.
- [ ] Update documentation and migration guides with new wiring steps.
- [ ] Run `_flake8.ps1` and ensure coverage ≥95%.
