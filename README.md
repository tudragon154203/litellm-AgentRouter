# LiteLLM Proxy

A lightweight proxy that provides an OpenAI-compatible API endpoint for multiple models including GPT-5, DeepSeek v3.2, Grok Code Fast-1, and GLM-4.6.

## Quick Start

```bash
# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start with Docker Compose
docker-compose up --build
```

The proxy starts on `http://localhost:4000`.

## Configuration

### Multi-Model Setup (Recommended)

```bash
# .env file
PROXY_MODEL_KEYS=gpt5,deepseek,grok,glm

# GPT-5 configuration
MODEL_GPT5_UPSTREAM_MODEL=gpt-5
MODEL_GPT5_REASONING_EFFORT=medium

# DeepSeek v3.2 configuration
MODEL_DEEPSEEK_UPSTREAM_MODEL=deepseek-v3.2
MODEL_DEEPSEEK_REASONING_EFFORT=medium

# Grok Code Fast-1 configuration
MODEL_GROK_UPSTREAM_MODEL=grok-code-fast-1
MODEL_GROK_REASONING_EFFORT=high

# GLM-4.6 configuration
MODEL_GLM_UPSTREAM_MODEL=glm-4.6
# Note: GLM-4.6 does not support reasoning_effort parameter

# Global settings
OPENAI_BASE_URL=https://agentrouter.org/v1
OPENAI_API_KEY=your-api-key
LITELLM_MASTER_KEY=sk-local-master
```

### CLI Configuration

```bash
python -m src.main \
  --model-spec "key=gpt5,alias=gpt-5,upstream=gpt-5,reasoning=medium" \
  --model-spec "key=deepseek,alias=deepseek-v3.2,upstream=deepseek-v3.2" \
  --model-spec "key=grok,alias=grok-code-fast-1,upstream=grok-code-fast-1,reasoning=high" \
  --model-spec "key=glm,alias=glm-4.6,upstream=glm-4.6"
```

## Client Usage

Configure OpenAI-compatible clients with:

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-local-master",
    base_url="http://localhost:4000"
)

response = client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Droid CLI Configuration

Configure Droid CLI in `~/.factory/config.json`:

```json
{
  "model_display_name": "ChatGPT 5 (AgentRouter - local proxy)",
  "model": "gpt-5",
  "base_url": "http://localhost:4000/v1",
  "api_key": "sk-local-master",
  "provider": "generic-chat-completion-api",
  "max_tokens": 8192
}
```

## Multi-Upstream Configuration

Configure models from multiple upstream providers to access different LLM services through a single proxy:

```bash
# Define upstream providers
UPSTREAM_AGENTROUTER_BASE_URL=https://agentrouter.org/v1
UPSTREAM_AGENTROUTER_API_KEY_ENV=AGENTROUTER_API_KEY

UPSTREAM_HUBS_BASE_URL=https://api.hubs.com/v1
UPSTREAM_HUBS_API_KEY_ENV=HUBS_API_KEY

# Configure models with upstream references
PROXY_MODEL_KEYS=gpt5,claude45

MODEL_GPT5_UPSTREAM=agentrouter
MODEL_GPT5_UPSTREAM_MODEL=gpt-5

MODEL_CLAUDE45_UPSTREAM=hubs
MODEL_CLAUDE45_UPSTREAM_MODEL=claude-4.5-sonnet

# Set API keys
AGENTROUTER_API_KEY=sk-your-agentrouter-key
HUBS_API_KEY=sk-your-hubs-key
```

**Configuration Precedence:**
- Models with `MODEL_<KEY>_UPSTREAM` use the specified upstream's base URL and API key
- Models without `MODEL_<KEY>_UPSTREAM` use global defaults (`OPENAI_BASE_URL`, `OPENAI_API_KEY`)
- Upstream names are case-insensitive (`HUBS`, `hubs`, `Hubs` all work)

**Backward Compatibility:**
Existing single-upstream configurations continue to work without changes. Simply omit the `MODEL_<KEY>_UPSTREAM` variable to use global defaults.

## Features

- **Multi-Model Support**: Run multiple models simultaneously
- **Multi-Upstream Support**: Aggregate models from different providers
- **OpenAI-Compatible**: Drop-in replacement for OpenAI API
- **Reasoning Control**: Adjustable reasoning effort (none/low/medium/high)
- **Request Telemetry**: Structured JSON logging for observability
- **Docker Ready**: Pre-configured containerization

## Development

```bash
# Install dependencies
pip install -e ".[test]"

# Run tests
pytest

# Local development
python -m src.main
```

## License

MIT License - see [LICENSE](LICENSE) file.