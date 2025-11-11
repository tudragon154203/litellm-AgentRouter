# Node.js Upstream Proxy

**Status**: ✅ Implemented  
**Priority**: High  
**Complexity**: High  
**Implementation Date**: November 2025

## Summary

The Node.js upstream proxy feature successfully routes LiteLLM traffic through a Node.js helper service to reach upstream APIs that block Python clients. The implementation is production-ready with comprehensive test coverage, Docker support, and graceful error handling.

**Key Achievements**:
- ✅ Modular Node.js HTTP proxy with OpenAI client integration
- ✅ Python subprocess management with lifecycle control
- ✅ Docker Compose support with separate services and health checks
- ✅ Comprehensive test coverage (Python >95%, Node unit + integration)
- ✅ Streaming and non-streaming response support
- ✅ Structured logging and telemetry integration
- ✅ Graceful shutdown and cleanup handling

## Problem Statement

- The current launcher relies on LiteLLM's Python OpenAI provider to call the upstream `agentrouter.org` endpoint, but the Python client is now blocked and the proxy can no longer reach the upstream server.
- A working workaround already exists in `demo/nodejs/qwen_code_openai_working_nodejs.py`, which demonstrates that the same upstream can be reached from the Node.js OpenAI client. We therefore need to replace the Python upstream plumbing with a Node.js component while keeping the existing OpenAI-compatible surface untouched.
- The migration must remain manageable within the current modular architecture (`src/config/`, `src/main.py`, `src/proxy.py`, `src/utils.py`, `src/telemetry/`) and must not regress telemetry, configuration, or coverage guarantees.

## Testing & Acceptance Criteria

✅ **All acceptance criteria met**

1. **Node unit tests**: ✅ Implemented using `node --test` in `node/tests/unit/` covering:
   * Request forwarding from `/v1/chat/completions` and `/v1/completions` to the OpenAI client
   * Header population (including QwenCode user agent via `NODE_USER_AGENT`)
   * Error paths (client failures, upstream errors, timeouts)
   * Configurable timeouts/ports via environment variables
   * Run via `npm run test:unit`

2. **Python unit tests**: ✅ Comprehensive coverage in `tests/unit/`:
   * `tests/unit/cli/test_cli.py` - CLI flag parsing for `NODE_UPSTREAM_PROXY_ENABLE`
   * `tests/unit/config/test_entrypoint.py` - Entrypoint starts Node helper process and cleanup
   * `tests/unit/config/parsing/test_prepare_config.py` - Config generation with Node proxy enabled
   * `tests/unit/node/test_process.py` - NodeProxyProcess subprocess management
   * `tests/unit/utils/test_utils.py` - Cleanup handler registration
   * Coverage maintained above 95%

3. **Integration tests**: ✅ Full stack validation in `tests/integration/`:
   * `tests/integration/node/test_node_upstream_proxy.py` - End-to-end Node proxy flow
   * `tests/integration/api/conftest.py` - Session-scoped Node proxy fixture for API tests
   * `tests/integration/api/test_real_*.py` - Real API calls through Node proxy
   * Tests skip gracefully when Node.js is not available
   * Telemetry and response shapes validated as OpenAI-compatible

4. **Linting & formatting**: ✅ Code passes `_flake8.ps1` checks with max line length 140

## Implemented Solution

- **Node helper service**: ✅ Implemented as modular Node.js HTTP service in `node/`:
  * `node/main.mjs` - Main entry point with signal handling (SIGINT, SIGTERM)
  * `node/lib/proxy.mjs` - Proxy factory with configuration and client injection
  * `node/lib/server.mjs` - HTTP server using Node's built-in `http` module
  * `node/lib/router.mjs` - Request routing with streaming support
  * `node/lib/routes.mjs` - Route handlers for `/v1/chat/completions` and `/v1/completions`
  * `node/lib/client.mjs` - OpenAI client factory with timeout configuration
  * `node/lib/config.mjs` - Configuration management from environment variables
  * `node/lib/http-utils.mjs` - HTTP utilities for headers and body parsing
  * `node/lib/logger.mjs` - Structured JSON logging
  * Listens on port 4000 by default, forwards to `OPENAI_BASE_URL` (default: `https://agentrouter.org/v1`)
  * Supports both streaming and non-streaming responses
  * Preserves headers including `x-request-id` for request correlation

- **Process supervision**: ✅ Implemented in `src/node/process.py`:
  * `NodeProxyProcess` class manages subprocess lifecycle
  * Spawns Node helper with `subprocess.Popen`
  * Injects `NODE_USER_AGENT` from `utils.build_user_agent()`
  * Forwards `OPENAI_BASE_URL` and `OPENAI_API_KEY` to Node environment
  * Graceful shutdown with 15-second timeout before force kill
  * PID stored in `NODE_UPSTREAM_PROXY_PID` environment variable
  * Cleanup handler registered via `utils.register_node_proxy_cleanup()`

- **Configuration handoff**: ✅ Implemented in `src/config/entrypoint.py`:
  * When `NODE_UPSTREAM_PROXY_ENABLE=1` (default), detects deployment mode:
    - Docker Compose: Uses `http://node-proxy:4000/v1` (separate service)
    - Single container: Starts subprocess at `http://127.0.0.1:4000/v1`
  * Overrides `global_upstream_base` in generated LiteLLM config
  * Preserves original `OPENAI_BASE_URL` for Node helper to use
  * Logs substitution for debugging
  * CLI flag `--no-node-upstream-proxy` disables feature

- **Docker/compose updates**: ✅ Production-ready deployment:
  * `Dockerfile` installs Node.js runtime and npm dependencies
  * `package.json` defines OpenAI client dependency and test scripts
  * `docker-compose.yml` defines two services:
    - `node-proxy`: Standalone Node service with health check
    - `litellm-proxy`: Python proxy that routes through Node service
  * Volume mounts for live development (`./node`, `./src`)
  * `entrypoint.sh` delegates to `python -m src.config.entrypoint`
  * Both containers share `.env` file for configuration

- **Telemetry/logging discipline**: ✅ Structured logging throughout:
  * Node helper emits JSON logs: `{"node_proxy": {"event": "...", ...}}`
  * Python telemetry middleware captures usage, latency, and errors
  * `x-request-id` header forwarded for request correlation
  * Logs include: startup, request_received, request_completed, request_failed, streaming_error
  * Python telemetry logs include: status_code, upstream_model, usage, duration_s

## Architecture

**Request Flow (Docker Compose - Separate Services)**:
1. Client → `litellm-python-proxy:4000` (exposed to host)
2. Python proxy → `http://node-proxy:4000/v1` (internal docker network)
3. Node proxy → `https://agentrouter.org/v1` (upstream API)
4. Response streams back through Node → Python → Client

**Request Flow (Single Container - Subprocess)**:
1. `entrypoint.sh` → `python -m src.config.entrypoint`
2. Entrypoint spawns `NodeProxyProcess` subprocess
3. Node helper starts on `127.0.0.1:4000`
4. LiteLLM config generated with `api_base: http://127.0.0.1:4000/v1`
5. Client → Python proxy → Node subprocess → Upstream API
6. Response streams back preserving headers and latency

**Component Architecture**:
- **Python Layer** (`src/`):
  * `src/main.py` - Main entry point, orchestrates startup
  * `src/config/entrypoint.py` - Docker entrypoint, spawns Node proxy
  * `src/node/process.py` - Node subprocess management (`NodeProxyProcess` class)
  * `src/proxy.py` - LiteLLM proxy server wrapper
  * `src/middleware/` - Telemetry and reasoning filter middleware
  * `src/utils.py` - Cleanup handlers and signal management
  
- **Node Layer** (`node/`):
  * `node/main.mjs` - Entry point with signal handling (SIGINT, SIGTERM)
  * `node/lib/proxy.mjs` - Proxy factory (`createNodeUpstreamProxy`)
  * `node/lib/server.mjs` - HTTP server (`NodeProxyServer` class)
  * `node/lib/router.mjs` - Request routing (`NodeRequestRouter` class)
  * `node/lib/routes.mjs` - Endpoint handlers (`createRouteHandlers`)
  * `node/lib/client.mjs` - OpenAI client wrapper with timeout
  * `node/lib/config.mjs` - Configuration management (`NodeProxyConfig` class)
  * `node/lib/constants.mjs` - Default values and constants
  * `node/lib/http-utils.mjs` - HTTP utilities (headers, body parsing)
  * `node/lib/logger.mjs` - Structured JSON logging
  
- **Test Layer**:
  * `tests/unit/node/` - Python unit tests for subprocess management
  * `tests/unit/cli/` - CLI flag parsing tests
  * `tests/unit/config/` - Configuration and entrypoint tests
  * `tests/integration/node/` - End-to-end Node proxy tests
  * `tests/integration/api/` - Real API integration tests
  * `node/tests/unit/` - Node.js unit tests
  * `node/tests/integration/` - Node.js integration tests
  
- **Configuration Flow**:
  1. Environment variables loaded into `runtime_config`
  2. `NODE_UPSTREAM_PROXY_ENABLE` determines routing mode
  3. Node proxy started (subprocess or docker service)
  4. LiteLLM config generated with appropriate `api_base`
  5. `custom_llm_provider: openai` preserved for compatibility
  6. Cleanup handlers registered for graceful shutdown

## Configuration & Runtime

**Environment Variables**:
- `NODE_UPSTREAM_PROXY_ENABLE` (bool, default: `1`) - Enable/disable Node proxy routing
- `OPENAI_BASE_URL` (string, default: `https://agentrouter.org/v1`) - Upstream API base URL
- `OPENAI_API_KEY` (string, required) - Upstream API key
- `NODE_USER_AGENT` (string, auto-generated) - User agent for upstream requests
- `PORT` (int, default: `4000`) - Host port mapping for docker-compose

**CLI Flags**:
- `--no-node-upstream-proxy` - Disable Node proxy (overrides environment)
- `--config <path>` - Use existing config file (bypasses Node proxy logic)
- `--print-config` - Print generated config and exit

**Runtime Behavior**:
- All configuration values flow through `src.config.config.runtime_config`
- Node helper reads `NODE_USER_AGENT` for QwenCode UA string
- Node helper logs `OPENAI_BASE_URL` on startup for debugging
- Node helper listens on port `4000` (matches LiteLLM convention)
- Automatic detection of docker-compose vs single-container mode
- Graceful fallback if Node.js runtime not available (error message + exit)

**Configuration Precedence** (highest to lowest):
1. CLI flags (`--no-node-upstream-proxy`)
2. Environment variables (`NODE_UPSTREAM_PROXY_ENABLE`)
3. Default values (Node proxy enabled)

## Rollout & Migration

✅ **Completed - Feature is production-ready**

**Implementation Timeline**:
1. ✅ Node helper implemented in `node/main.mjs` with modular architecture
2. ✅ Node unit tests added (`node --test`) covering all core functionality
3. ✅ Python subprocess management implemented in `src/node/process.py`
4. ✅ Python unit tests added for CLI, config, entrypoint, and process management
5. ✅ Integration tests added for end-to-end validation
6. ✅ Dockerfile updated to install Node.js and npm dependencies
7. ✅ docker-compose.yml configured with separate services and health checks
8. ✅ All tests passing (`npm test`, `pytest`)
9. ✅ Linting clean (`_flake8.ps1`)
10. ✅ Coverage maintained above 95%

**Deployment Modes**:
- **Docker Compose** (recommended): Two separate services with health checks
- **Single Container**: Node subprocess managed by Python entrypoint
- **Local Development**: Direct execution with `python -m src.main`

**Error Handling**:
- Missing Node.js binary: Clear error message + exit code 1
- Missing OPENAI_API_KEY: Clear error message + exit code 1
- Node helper crash: Subprocess monitoring and cleanup
- Upstream connection errors: Proper HTTP status codes forwarded to client

## Verification & Testing

**Automated Testing**:
```bash
# Node unit tests
npm run test:unit

# Node integration tests  
npm run test:integration

# All Node tests
npm test

# Python unit tests
pytest tests/unit/

# Python integration tests
pytest tests/integration/

# All Python tests with coverage
pytest

# Linting
.\_flake8.ps1

# Formatting
.\_autopep8.ps1
```

**Manual Testing**:
```bash
# Build and start containers
docker-compose build
docker-compose up -d

# Check container status
docker-compose ps

# View logs
docker logs litellm-python-proxy
docker logs litellm-node-proxy

# Test health endpoint
curl -H "Authorization: Bearer sk-local-master" http://localhost:4000/health

# Test chat completion
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-local-master" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'

# Stop containers
docker-compose down
```

**Coverage Reports**:
- Python coverage: `tests/htmlcov/index.html` (maintained above 95%)
- Node coverage: Not yet implemented (future enhancement)

**Documentation**:
- ✅ This PRD serves as authoritative reference
- ✅ Code comments in all modules
- ✅ README.md includes Node proxy information
- ✅ Steering rules updated in `.kiro/steering/`

## Assumptions & Risks

**Validated Assumptions**:
- ✅ Node.js is available in Docker image (installed via `apt-get`)
- ✅ Node helper faithfully reproduces OpenAI-compatible API surface
- ✅ Latency overhead is minimal (Node proxy adds ~10-50ms)
- ✅ Streaming responses work correctly through Node layer
- ✅ Headers and status codes preserved accurately

**Known Limitations**:
- Node helper currently supports only `/v1/chat/completions` and `/v1/completions`
- Future endpoints (embeddings, moderation, audio) require Node helper extension
- Node.js runtime required in deployment environment (not optional)
- Single point of failure if Node helper crashes (mitigated by subprocess monitoring)

**Mitigation Strategies**:
- Health checks in docker-compose detect Node helper failures
- Subprocess monitoring and cleanup prevent zombie processes
- Clear error messages guide troubleshooting
- Graceful shutdown handling prevents resource leaks
- Integration tests validate end-to-end functionality

**Future Enhancements**:
- Add support for additional OpenAI endpoints (embeddings, moderation, audio)
- Implement Node test coverage reporting
- Add retry logic for transient upstream failures
- Implement connection pooling for better performance
- Add metrics/monitoring for Node helper performance
