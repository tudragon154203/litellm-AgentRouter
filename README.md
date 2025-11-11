# LiteLLM Proxy

A lightweight proxy that provides an OpenAI-compatible API endpoint for multiple models including GPT-5, DeepSeek v3.2, Grok Code Fast-1, and GLM-4.6.

## Quick Start

```bash
# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start both services (required)
docker-compose up -d --build
```

The proxy starts on `http://localhost:4000`.

**Note**: Both `node-proxy` and `litellm-proxy` services must be running. The Node.js upstream proxy handles all external API calls, while the Python proxy provides the OpenAI-compatible interface.

## Architecture

### Node.js Upstream Proxy (Required)

All upstream traffic routes through a Node.js proxy using the official `openai` client, solving Python client compatibility issues. This service is **required** for the proxy to function.

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                           │
│                    (litellm-network)                         │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │   node-proxy     │         │  litellm-proxy   │         │
│  │   (required)     │         │   (required)     │         │
│  │  Node.js v20     │◄────────│  Python 3.12     │         │
│  │  Port: 4000      │         │  Port: 4000      │         │
│  │  (internal only) │         │  (exposed)       │         │
│  └──────────────────┘         └──────────────────┘         │
│         │                              │                    │
└─────────┼──────────────────────────────┼────────────────────┘
          │                              │
          ▼                              ▼
   agentrouter.org              localhost:4000
```

**Docker Compose Usage** (both services start together):

```bash
# Start both services
docker-compose up -d --build

# Stop services
docker-compose down

# View logs from both services
docker-compose logs -f

# View logs from specific service
docker-compose logs -f node-proxy
docker-compose logs -f litellm-proxy
```

Both `node-proxy` and `litellm-proxy` containers start automatically with service discovery via Docker DNS. The Python proxy automatically connects to the Node proxy at `http://node-proxy:4000`.

**Configuration**:
```bash
NODE_UPSTREAM_PROXY_ENABLE=1  # Enable proxy (default, required)
# URL is auto-detected: http://node-proxy:4000/v1 (docker-compose) or http://127.0.0.1:4000/v1 (local)
```

**Testing**: `npm test`

## Configuration

All configuration is done via environment variables in `.env` file. See `.env.example` for all available options.

### Core Settings

```bash
# Port for the proxy (default: 4000)
PORT=4000

# Master key for client authentication
LITELLM_MASTER_KEY=sk-local-master

# Enable streaming responses (default: true)
STREAMING_ENABLE=true

# Enable telemetry logging (default: 1)
TELEMETRY_ENABLE=1
```

### Node.js Upstream Proxy (Required)

```bash
# Enable Node.js upstream proxy (required, default: 1)
NODE_UPSTREAM_PROXY_ENABLE=1

# The proxy URL is automatically detected:
# - Docker Compose: http://node-proxy:4000/v1 (separate service)
# - Local/Single Container: http://127.0.0.1:4000/v1 (subprocess)
```

### Upstream API Configuration

```bash
# Global upstream settings (used by all models unless overridden)
OPENAI_BASE_URL=https://agentrouter.org/v1
OPENAI_API_KEY=your-api-key
MAX_TOKENS=8192

# Default reasoning effort (none/low/medium/high)
REASONING_EFFORT=medium
```

### Multi-Model Setup

Define multiple models using the `PROXY_MODEL_KEYS` pattern:

```bash
# Define model keys (comma-separated)
PROXY_MODEL_KEYS=GPT5,DEEPSEEK,GROK,GLM

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
# Note: GLM does not support reasoning_effort
```

### Single Model Setup

For a simple single-model deployment:

```bash
PROXY_MODEL_KEYS=PRIMARY
MODEL_PRIMARY_UPSTREAM_MODEL=gpt-5
MODEL_PRIMARY_REASONING_EFFORT=medium
```

### Per-Model Overrides

Each model can override global settings:

```bash
# Override base URL for specific model
MODEL_GPT5_UPSTREAM_BASE=https://custom-endpoint.com/v1

# Override reasoning effort per model
MODEL_DEEPSEEK_REASONING_EFFORT=high
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
  "base_url": "http://localhost:4000",
  "api_key": "sk-local-master",
  "provider": "generic-chat-completion-api",
  "max_tokens": 8192
}
```

## Features

- **Multi-Model Support**: Run multiple models simultaneously
- **OpenAI-Compatible**: Drop-in replacement for OpenAI API
- **Reasoning Control**: Adjustable reasoning effort (none/low/medium/high)
- **Request Telemetry**: Structured JSON logging for observability
- **Docker Ready**: Pre-configured containerization

## Development

### Docker Development (Recommended)

```bash
# Start with live code reloading
docker-compose up --build

# Run tests in container
docker-compose exec litellm-proxy pytest
```

### Local Development

```bash
# Install dependencies
pip install -e ".[test]"

# Start Node proxy (required)
cd node
npm install
npm start  # Runs on port 4000

# In another terminal, start Python proxy
python -m src.main  # Connects to Node proxy at localhost:4000

# Run tests
pytest
```

**Note**: For local development, you must run both the Node.js proxy and Python proxy. The Node proxy must start first on port 4000, then the Python proxy will connect to it.

## License

MIT License - see [LICENSE](LICENSE) file.
