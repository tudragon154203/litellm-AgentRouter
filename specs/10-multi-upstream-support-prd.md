# Multi-Upstream Support PRD

## Overview
The LiteLLM Local Gateway currently uses a single upstream configuration (OPENAI_BASE_URL, OPENAI_API_KEY) for all models. This limitation prevents aggregating models from multiple providers (e.g., AgentRouter, Hubs, direct provider APIs) into a unified OpenAI-compatible interface. This feature enables per-model upstream endpoint configuration, allowing the proxy to route requests to different API providers based on the model being accessed.

**Central Goal**: Enable the LiteLLM proxy to support multiple upstream API endpoints simultaneously, allowing each model to specify its own upstream provider while maintaining backward compatibility with existing single-upstream configurations.

## Current State
- All models share global OPENAI_BASE_URL and OPENAI_API_KEY configuration
- No mechanism exists to route different models to different upstream providers
- Configuration system lacks upstream registry or per-model upstream references
- YAML rendering assumes single upstream for all models
- No validation for upstream model name uniqueness across providers

## User Stories
- *Developer* wants to configure models from multiple upstream providers (AgentRouter, Hubs, direct APIs) through a single local proxy endpoint
- *Developer* wants to add Hubs API models alongside existing AgentRouter models without conflicts
- *Operations engineer* needs clear error messages when upstream configuration is invalid or incomplete
- *Contributor* wants backward compatibility so existing single-upstream configurations continue working without modification
- *QA engineer* needs validation that prevents duplicate upstream model names across providers

## Functional Requirements
1. **Upstream Registry** (`src/config/parsing.py`):
   - Parse UPSTREAM_<NAME>_BASE_URL and UPSTREAM_<NAME>_API_KEY_ENV environment variables
   - Build registry mapping upstream names (case-insensitive) to UpstreamSpec objects
   - Validate each upstream has both BASE_URL and API_KEY_ENV defined
   - Raise clear errors for incomplete upstream definitions

2. **Per-Model Upstream References** (`src/config/models.py`):
   - Add upstream_name field to ModelSpec dataclass
   - Support MODEL_<KEY>_UPSTREAM environment variable for specifying upstream per model
   - Resolve upstream_base and upstream_key_env from registry when upstream_name is set
   - Fall back to global OPENAI_BASE_URL and OPENAI_API_KEY when no upstream specified

3. **Model Specification Validation** (`src/config/parsing.py`):
   - Validate upstream_model names are unique across all configured models
   - Detect and report duplicate upstream model names with clear error messages
   - Run validation before proxy startup to prevent runtime conflicts

4. **YAML Rendering** (`src/config/rendering.py`):
   - Always include api_base and api_key in litellm_params for each model
   - Use model's upstream_base if set, otherwise use global default
   - Use model's upstream_key_env if set, otherwise use global default
   - Generate valid LiteLLM proxy configuration supporting multiple upstreams

5. **Documentation & Examples**:
   - Document UPSTREAM_* environment variable pattern in README.md
   - Provide complete .env.example showing multiple upstream configuration
   - Explain precedence: model-specific settings override global defaults
   - Include examples for common providers (AgentRouter, Hubs)

## Non-Functional Requirements
- Maintain ≥95% test coverage for all new and modified code
- Preserve backward compatibility with existing single-upstream configurations
- Support concurrent requests to models with different upstream endpoints without interference
- Conform to flake8 linting standards (max line length 140)
- Ensure zero performance degradation for single-upstream use cases

## Test Strategy (TDD First)
1. **Unit Tests** (write before implementation, expect failures):
   - `tests/unit/config/test_parsing.py`: upstream registry parsing, case-insensitive name matching, incomplete upstream detection, upstream resolution in model loading
   - `tests/unit/config/test_models.py`: ModelSpec with upstream_name field, backward compatibility
   - `tests/unit/config/test_rendering.py`: YAML rendering with per-model upstreams, api_base/api_key inclusion
   - `tests/unit/config/test_validation.py`: duplicate upstream model name detection

2. **Integration Tests**:
   - `tests/integration/test_multi_upstream_routing.py`: verify generated YAML routes models to correct upstreams
   - `tests/integration/test_backward_compatibility.py`: verify legacy single-upstream configs work unchanged

3. **Docker Tests**:
   - Build Docker image with multi-upstream changes
   - Test multi-upstream configuration in container
   - Test backward compatibility in container

## Implementation Plan (High-Level)
1. Draft failing tests for upstream registry parsing, ModelSpec enhancements, and validation
2. Implement UpstreamSpec dataclass and upstream registry parsing
3. Enhance ModelSpec with upstream_name field and update model loading logic
4. Implement validate_model_specs() for duplicate detection
5. Update YAML rendering to always include api_base and api_key per model
6. Update documentation (README.md, .env.example)
7. Write integration tests for multi-upstream routing and backward compatibility
8. Verify code quality (coverage ≥95%, zero flake8 errors)
9. Test in Docker container with multiple upstream configurations

## Detailed Design

### Upstream Registry
- **UpstreamSpec Dataclass** (`src/config/models.py`):
  ```python
  @dataclass
  class UpstreamSpec:
      name: str
      base_url: str
      api_key_env: str
  ```

- **Registry Parsing** (`src/config/parsing.py`):
  - Scan environment for UPSTREAM_<NAME>_BASE_URL and UPSTREAM_<NAME>_API_KEY_ENV
  - Extract upstream name (case-insensitive), normalize to lowercase
  - Group by upstream name, validate both fields present
  - Return `dict[str, UpstreamSpec]` mapping lowercase names to specs
  - Raise ValueError for incomplete upstreams with clear message

### ModelSpec Enhancement
- Add `upstream_name: Optional[str] = None` field to ModelSpec
- Maintain backward compatibility (defaults to None)
- Support both upstream_name (new) and upstream_base/upstream_key_env (legacy)

### Model Loading with Upstream Resolution
- Call `parse_upstream_registry()` at start of `load_model_specs_from_env()`
- Parse MODEL_<KEY>_UPSTREAM environment variable
- Normalize upstream name to lowercase
- Look up upstream in registry if MODEL_<KEY>_UPSTREAM is set
- Resolve base_url and api_key_env from UpstreamSpec
- Fall back to global OPENAI_BASE_URL and OPENAI_API_KEY if no upstream specified
- Raise ValueError if MODEL_<KEY>_UPSTREAM references non-existent upstream

### Validation
- **validate_model_specs()** function in `src/config/parsing.py`:
  - Collect all upstream_model values from ModelSpec list
  - Detect duplicates using set comparison
  - Raise ValueError listing conflicting model keys and upstream model name
- Integrate into `prepare_config()` after loading model specs, before YAML rendering

### YAML Rendering
- Update `render_model_entry()` in `src/config/rendering.py`:
  - Always include api_base in litellm_params (from model spec or global)
  - Always include api_key in litellm_params (from model spec or global)
  - Remove conditional logic that omits these fields
  - Use `os.environ/<VAR_NAME>` reference format for api_key

### Environment Variable Schema
```bash
# Upstream registry
UPSTREAM_AGENTROUTER_BASE_URL=https://agentrouter.example.com/v1
UPSTREAM_AGENTROUTER_API_KEY_ENV=AGENTROUTER_API_KEY

UPSTREAM_HUBS_BASE_URL=https://hubs.example.com/v1
UPSTREAM_HUBS_API_KEY_ENV=HUBS_API_KEY

# Per-model upstream references
MODEL_GPT5_UPSTREAM=agentrouter
MODEL_CLAUDE_UPSTREAM=hubs

# Global defaults (backward compatibility)
OPENAI_BASE_URL=https://default.example.com/v1
OPENAI_API_KEY=default-key
```

## Risks & Mitigations
- **Breaking Changes**: Existing configs might break if validation is too strict. Mitigate by maintaining backward compatibility and only validating new features.
- **Duplicate Model Names**: Multiple upstreams might expose same model name. Mitigate with validation that detects and reports duplicates before startup.
- **Configuration Complexity**: Multiple upstreams increase configuration surface. Mitigate with clear documentation and examples.
- **Performance**: Registry parsing adds startup overhead. Mitigate by caching registry and only parsing once.

## Verification Steps
```bash
# 1. Create failing tests first
pytest tests/unit/config/ -v  # new upstream tests
pytest tests/integration/test_multi_upstream_routing.py  # integration tests

# 2. After implementation
pytest  # full suite
pytest --cov=src --cov-report=term-missing  # verify ≥95% coverage
./_flake8.ps1  # verify zero linting errors

# 3. Docker verification
docker-compose up --build  # test in container
```

## Assumptions
- Upstream providers expose OpenAI-compatible APIs that LiteLLM can proxy
- API keys for different upstreams are stored in separate environment variables
- Upstream model names are unique within each upstream provider
- Configuration is loaded once at startup (no hot-reloading of upstream registry)

## Follow-Up Opportunities
- Support dynamic upstream registration via API endpoint
- Add upstream health checks and automatic failover
- Implement upstream-level rate limiting and retry policies
- Support upstream authentication methods beyond API keys (OAuth, JWT)
- Add telemetry for per-upstream request metrics

## TODO Checklist
- [x] Draft failing unit tests for upstream registry parsing
- [x] Implement UpstreamSpec dataclass
- [x] Implement parse_upstream_registry() function
- [x] Add upstream_name field to ModelSpec
- [x] Enhance load_model_specs_from_env() for upstream resolution
- [x] Implement validate_model_specs() for duplicate detection
- [x] Update render_model_entry() to always include api_base and api_key
- [x] Write unit tests for all new functionality
- [x] Update README.md with multi-upstream documentation
- [x] Update .env.example with multi-upstream examples
- [x] Write integration tests for multi-upstream routing
- [x] Write integration tests for backward compatibility
- [x] Verify coverage ≥95% and zero flake8 errors
- [x] Build Docker image with changes
- [ ] Test multi-upstream configuration in Docker container
- [ ] Test backward compatibility in Docker container
