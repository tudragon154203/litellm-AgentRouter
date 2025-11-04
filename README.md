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

## Features

- **Multi-Model Support**: Run multiple models simultaneously
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