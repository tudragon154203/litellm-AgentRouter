# GLM-4.6 Integration PRD (Completion)
> **Update:** `PROXY_MODEL_KEYS` is deprecated; autodiscovered `MODEL_<KEY>_*` variables now replace the legacy pattern.

## Overview
The LiteLLM proxy launcher has partial integration for GLM-4.6 (Zhipu AI) with working demo scripts and API tests. This PRD documents the completion of the integration to make GLM-4.6 a first-class model alongside GPT-5, DeepSeek v3.2, and Grok Code Fast-1.

**Current State**:
- ✅ Model capabilities defined in `MODEL_CAPS` (supports_reasoning: False)
- ✅ Demo script works with environment variables
- ✅ Real API integration tests verify basic functionality
- ❌ Missing unit tests for GLM-4.6 configuration
- ❌ Missing documentation examples
- ❌ No multi-model integration tests
- ❌ No integration PRD

**Integration Goal**: Complete the GLM-4.6 integration by adding missing tests and documentation to match the standards set by Grok Code Fast-1 and DeepSeek v3.2 integrations.

## User Stories
- *Platform engineer* wants to run GLM-4.6 alongside GPT-5/DeepSeek/Grok in multi-model proxy configuration with consistent setup patterns.
- *Chinese market customer* needs reliable Chinese language support with native GLM-4.6 model without reasoning parameter overhead.
- *QA analyst* requires comprehensive test coverage proving GLM-4.6 works in isolation and multi-model scenarios.
- *Developer* needs clear documentation showing how to configure GLM-4.6 with environment variables and CLI flags.

## Functional Requirements (Completion Tasks)

**Already Implemented**:
- ✅ Model capabilities: `"glm-4.6": {"supports_reasoning": False}` in `src/config/models.py:77`
- ✅ Multi-model configuration support via `PROXY_MODEL_KEYS`
- ✅ Real API tests: `tests/integration/api/test_real_glm_api.py`
- ✅ Demo script: `demo/glm/test_glm_4.6.py`
- ✅ Reasoning effort filtering (automatically omitted for GLM-4.6)

**Required Additions**:
1. **Unit Tests** (`tests/unit/config/test_config.py`):
   - Test GLM-4.6 presence in MODEL_CAPS
   - Test reasoning capability is False
   - Test config rendering works correctly
   - Test environment variable configuration
   - Test reasoning_effort filtering (even if specified, it should be omitted)

2. **Documentation** (`README.md`):
   - Add GLM-4.6 to model description
   - Add GLM to multi-model environment example
   - Add GLM to CLI configuration example
   - Note: GLM does not support reasoning_effort parameter

3. **Environment Examples** (`.env.example`):
   - Add GLM-4.6 configuration section
   - Clarify GLM does not support reasoning_effort
   - Show GLM in multi-model setup

4. **Multi-Model Integration Tests** (`tests/integration/multi_model/test_multi_model_integration.py`):
   - Test GLM-4.6 in multi-model configuration
   - Test reasoning_effort filtering for GLM-4.6
   - Test startup message includes GLM-4.6

5. **Integration PRD**: This document

## Non-Functional Requirements (Maintain Standards)
- **Test Coverage**: Maintain 95%+ coverage (additions should not decrease coverage)
- **Performance**: Zero impact (leverages existing architecture)
- **Consistency**: Follow patterns from Grok and DeepSeek integrations
- **Documentation**: Match quality of existing model documentation

## GLM-4.6 Specific Characteristics

**Provider**: Zhipu AI (智谱AI)
**API Base**: `https://open.bigmodel.cn/api/paas/v4`
**API Compatibility**: OpenAI-compatible (via LiteLLM)
**Reasoning Support**: ❌ No (unlike GPT-5, DeepSeek, Grok)
**Streaming Support**: ✅ Yes
**Chinese Language**: ✅ Native support

**Key Difference from Other Models**:
GLM-4.6 does NOT support the `reasoning_effort` parameter. The configuration system automatically filters it out based on `MODEL_CAPS`, but tests must verify this behavior.

## Edge Cases (Already Handled)
All edge cases are handled by existing infrastructure:
- ✅ **Missing credentials**: Configuration validation rejects missing env vars
- ✅ **Reasoning effort specified**: Automatically filtered out based on MODEL_CAPS
- ✅ **Streaming errors**: Standard error handling applies
- ✅ **Chinese language support**: LiteLLM handles encoding automatically
- ✅ **Concurrent requests**: Thread-safe configuration system

## Implementation Plan (Completion)

**Step 1: Unit Tests** ✅ COMPLETED
- Add `TestGLM46Integration` class to `tests/unit/config/test_config.py`
- Tests: model presence, reasoning capability, config rendering, environment config, filtering

**Step 2: Documentation** ✅ COMPLETED
- Update `README.md` with GLM-4.6 examples
- Update `.env.example` with GLM configuration

**Step 3: Multi-Model Tests** ✅ COMPLETED
- Add GLM-4.6 multi-model integration tests
- Test reasoning_effort filtering behavior
- Test startup message includes GLM

**Step 4: Integration PRD** ✅ COMPLETED
- Document completion of GLM-4.6 integration

**Step 5: Validation** 🔄 PENDING
- Run test suite to verify all tests pass
- Check coverage remains ≥95%
- Run `_flake8.ps1` for lint compliance

## Verification Steps
```bash
# Run all tests
pytest

# Run specific GLM tests
pytest tests/unit/config/test_config.py::TestGLM46Integration -v
pytest tests/integration/multi_model/test_multi_model_integration.py::TestMultiModelIntegration::test_print_config_with_glm_4_6 -v

# Check coverage
pytest --cov=src --cov-report=term-missing

# Lint check
./_flake8.ps1

# Manual smoke test
PROXY_MODEL_KEYS=glm MODEL_GLM_UPSTREAM_MODEL=glm-4.6 python -m src.main --print-config
```

## Configuration Examples

### Environment Variables
```bash
# Single GLM-4.6 model
PROXY_MODEL_KEYS=glm
MODEL_GLM_UPSTREAM_MODEL=glm-4.6
GLM_API_KEY=your-glm-api-key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

### Multi-Model Setup
```bash
# GLM-4.6 with GPT-5 and DeepSeek
PROXY_MODEL_KEYS=gpt5,deepseek,glm
MODEL_GPT5_UPSTREAM_MODEL=gpt-5
MODEL_GPT5_REASONING_EFFORT=medium
MODEL_DEEPSEEK_UPSTREAM_MODEL=deepseek-v3.2
MODEL_DEEPSEEK_REASONING_EFFORT=medium
MODEL_GLM_UPSTREAM_MODEL=glm-4.6
# Note: GLM does not support reasoning_effort
```

### CLI Configuration
```bash
python -m src.main \
  --model-spec "key=gpt5,alias=gpt-5,upstream=gpt-5,reasoning=medium" \
  --model-spec "key=glm,alias=glm-4.6,upstream=glm-4.6" \
  --upstream-base https://agentrouter.org/v1
```

## Assumptions (All Valid)
- ✅ GLM-4.6 API is OpenAI-compatible (verified via existing tests)
- ✅ Multi-model architecture supports GLM-4.6 without modifications
- ✅ LiteLLM handles GLM-4.6 provider automatically
- ✅ Chinese language encoding works out of the box
- ✅ Reasoning effort filtering works based on MODEL_CAPS

## Integration Status

| Component | Status | Location |
|-----------|--------|----------|
| Model Capabilities | ✅ Complete | `src/config/models.py:77` |
| Unit Tests | ✅ Complete | `tests/unit/config/test_config.py:297-367` |
| Real API Tests | ✅ Complete | `tests/integration/api/test_real_glm_api.py` |
| Multi-Model Tests | ✅ Complete | `tests/integration/multi_model/test_multi_model_integration.py:294-426` |
| Demo Script | ✅ Complete | `demo/glm/test_glm_4.6.py` |
| README Documentation | ✅ Complete | `README.md:3,24,38-40,55` |
| Environment Examples | ✅ Complete | `.env.example:31,47-49` |
| Integration PRD | ✅ Complete | `specs/7-glm-4.6-integration-prd.md` |

## Follow-Up (Optional)
- Performance benchmarks vs GPT-5/DeepSeek/Grok
- Chinese language specific test cases
- Token usage optimization for Chinese text
- Cost analysis and rate limiting configuration
