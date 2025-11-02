# LiteLLM Local Gateway - Multi-Model Support

A modular LiteLLM proxy launcher that exposes an OpenAI-compatible API endpoint for multiple models including GPT-5 and DeepSeek v3.2. The proxy is useful when other local services expect the OpenAI client interface but you want to fan traffic out to any provider supported by LiteLLM.

## Project Structure

```
├── src/
│   ├── main.py          # Main entry point
│   ├── cli.py           # CLI argument parsing
│   ├── config.py        # Configuration management
│   ├── proxy.py         # Proxy server logic
│   ├── telemetry.py     # Request telemetry logging middleware
│   └── utils.py         # Utility functions
├── docker-compose.yml   # Docker Compose configuration

├── Dockerfile          # Docker image definition
├── pyproject.toml      # Python package configuration
├── .env.example        # Example environment variables
└── tests/              # Unit tests
```

## Prerequisites

- Python 3.8+
- Docker and Docker Compose (for containerized deployment)

## Quick Start

### Using Docker Compose (Recommended)

1. Copy the example environment file and configure your API key:

   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```
2. Start the proxy with Docker Compose:

   ```bash
   docker-compose up --build
   ```

The server will start on `http://localhost:4000` with live code reloading for development (via bind mount of ./src into the container).

## Multi-Model Configuration

The proxy supports running multiple models concurrently from a single instance. You can expose both GPT-5 and DeepSeek v3.2 (and additional models) simultaneously, allowing downstream clients to target either alias without restarting the service.

### Environment-Based Configuration (Recommended)

Configure multiple models using the new `PROXY_MODEL_KEYS` schema:

```bash
# Copy and configure environment
cp .env.example .env

# Edit .env with multi-model setup:
PROXY_MODEL_KEYS=gpt5,deepseek

# GPT-5 model configuration
MODEL_GPT5_ALIAS=gpt-5
MODEL_GPT5_UPSTREAM_MODEL=gpt-5
MODEL_GPT5_REASONING_EFFORT=medium

# DeepSeek v3.2 model configuration
MODEL_DEEPSEEK_ALIAS=deepseek-v3.2
MODEL_DEEPSEEK_UPSTREAM_MODEL=deepseek-v3.2
MODEL_DEEPSEEK_REASONING_EFFORT=medium

# Global defaults (used when per-model values omitted)
OPENAI_API_BASE=https://agentrouter.org/v1
OPENAI_API_KEY=sk-your-upstream-api-key
LITELLM_MASTER_KEY=sk-local-master
```

Start the proxy:

```bash
docker-compose up --build
```

Both models will be available:
- **GPT-5**: `http://localhost:4000` with model `"gpt-5"`
- **DeepSeek v3.2**: `http://localhost:4000` with model `"deepseek-v3.2"`

### CLI-Based Configuration

Alternatively, use `--model-spec` flags for quick multi-model setup:

```bash
python -m src.main \
  --model-spec "key=gpt5,alias=gpt-5,upstream=gpt-5,reasoning=medium" \
  --model-spec "key=deepseek,alias=deepseek-v3.2,upstream=deepseek-v3.2,reasoning=none"
```

### Single Model Configuration

For single-model deployments, use the new schema with one entry:

```bash
# Environment configuration
PROXY_MODEL_KEYS=primary
MODEL_PRIMARY_ALIAS=gpt-5
MODEL_PRIMARY_UPSTREAM_MODEL=gpt-5
MODEL_PRIMARY_REASONING_EFFORT=high
```

### Model-Specific Configuration

#### DeepSeek v3.2

DeepSeek v3.2 is fully supported with AgentRouter upstream:

```bash
# DeepSeek-only configuration
PROXY_MODEL_KEYS=deepseek
MODEL_DEEPSEEK_ALIAS=deepseek-v3.2
MODEL_DEEPSEEK_UPSTREAM_MODEL=deepseek-v3.2
MODEL_DEEPSEEK_REASONING_EFFORT=medium
```

**Recommended Settings for DeepSeek v3.2:**
- **Reasoning Effort**: `medium` (balanced performance)
- **Drop Params**: `true` (default, filters unsupported parameters)
- **Streaming**: `true` (default, enables real-time responses)

#### GPT-5

GPT-5 configuration supports the full range of reasoning controls:

```bash
# GPT-5 with high reasoning
PROXY_MODEL_KEYS=gpt5
MODEL_GPT5_ALIAS=gpt-5
MODEL_GPT5_UPSTREAM_MODEL=gpt-5
MODEL_GPT5_REASONING_EFFORT=high
```

**Recommended Settings for GPT-5:**
- **Reasoning Effort**: `high` (maximum quality for complex tasks)
- **Drop Params**: `true` (default)
- **Streaming**: `true` (default)

### Migration Notes

The proxy has transitioned from single-model environment variables to a multi-model schema:

**Legacy Variables (Retired):**
- `LITELLM_MODEL_ALIAS` → Use `PROXY_MODEL_KEYS` + `MODEL_<KEY>_ALIAS`
- `OPENAI_MODEL` → Use `MODEL_<KEY>_UPSTREAM_MODEL`
- `LITELLM_HOST` → Now hardcoded to `0.0.0.0`
- `LITELLM_WORKERS` → Now hardcoded to `1`
- `LITELLM_DEBUG` → Use `--debug` flag
- `LITELLM_DROP_PARAMS` → Use `--drop-params`/`--no-drop-params`

**New Required Schema:**
Even for single-model deployments, use `PROXY_MODEL_KEYS` with at least one entry.

**Example Migration:**
```bash
# Old way (retired)
LITELLM_MODEL_ALIAS=gpt-5
OPENAI_MODEL=gpt-5

# New way (required)
PROXY_MODEL_KEYS=primary
MODEL_PRIMARY_ALIAS=gpt-5
MODEL_PRIMARY_UPSTREAM_MODEL=gpt-5
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Local Development

1. Install dependencies and the package:

   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
2. Configure your environment variables (see `.env.example`)
3. Run the proxy:

   ```bash
   python -m src.main
   ```

## Configuration

The proxy provides sensible defaults that are configurable via CLI flags or environment variables:

- **Model Alias**: default gpt-5 (CLI: --alias)
- **Master Key**: default from LITELLM_MASTER_KEY (CLI: --master-key, or --no-master-key)
- **Host Interface**: default 0.0.0.0 (CLI: --host)
- **Port**: default 4000 (env PORT or CLI: --port)
- **Workers**: default 1 (CLI: --workers)
- **Debug**: default false (CLI: --debug, --detailed-debug)
- **Drop Params**: default true (CLI: --drop-params / --no-drop-params)

Configurable settings via environment variables:

- **PORT**: Port for the proxy (default: 4000)
- **LITELLM_MASTER_KEY**: Master key for authentication (default: sk-local-master)
- **OPENAI_MODEL**: Upstream model (default: gpt-5)
- **OPENAI_BASE_URL**: Upstream API base URL (default: https://api.openai.com/v1)
- **OPENAI_API_KEY**: Your OpenAI API key
- **REASONING_EFFORT**: Reasoning effort level for supported models (default: medium)
- **IS_STREAMING**: Enable streaming mode (default: true)
- CLI `--model` default is `gpt-5`
- Note: `set_verbose` in the generated config mirrors the streaming flag (true when streaming is enabled)

### CLI Configuration

Use `--model-spec` for command-line multi-model configuration:

```bash
# Multiple models
python -m src.main \
  --model-spec "key=gpt5,alias=gpt-5,upstream=gpt-5,reasoning=high" \
  --model-spec "key=deepseek,alias=deepseek-v3.2,upstream=deepseek-v3.2"

# Single model with custom base URL
python -m src.main \
  --model-spec "key=primary,alias=my-model,upstream=gpt-5,base=https://api.custom.com"

# With global settings
python -m src.main \
  --model-spec "key=test,alias=test-model,upstream=gpt-5" \
  --upstream-base "https://agentrouter.org/v1" \
  --master-key "sk-custom-master" \
  --no-drop-params
```

### Legacy Configuration

The following single-model variables are **retired**:
- `LITELLM_MODEL_ALIAS`, `OPENAI_MODEL`, `LITELLM_HOST`, `LITELLM_WORKERS`, `LITELLM_DEBUG`, `LITELLM_DROP_PARAMS`

Use the new multi-model schema even for single-model deployments.

### Using Custom Configuration

You can provide your own LiteLLM configuration file:

```bash
# With Docker Compose
docker-compose run --rm litellm-proxy python -m src.main --config /path/to/config.yaml

# Local development
python -m src.main --config /path/to/config.yaml
```

### Print Generated Configuration

To see the auto-generated configuration:

```bash
python -m src.main --print-config
```

## Reasoning Effort Configuration

The proxy supports controlling reasoning capabilities for models that benefit from adjustable reasoning effort (like AgentRouter's GPT-5 and DeepSeek v3.2). This feature allows you to balance response quality against computational cost.

### Supported Reasoning Levels

- **none**: No reasoning effort optimization
- **low**: Minimal reasoning optimization (faster responses)
- **medium**: Balanced reasoning (default)
- **high**: Maximum reasoning optimization (slower but higher quality)

### Configuration Methods

#### Environment Variable

```bash
export REASONING_EFFORT=high
python -m src.main
```

#### CLI Override

```bash
python -m src.main --reasoning-effort medium
```

#### Combined Usage

```bash
export REASONING_EFFORT=low
python -m src.main \
  --reasoning-effort high \
  --alias gpt-5-high-reasoning \
  --model gpt-5 \
  --upstream-base https://agentrouter.org/v1
```

### Generated Configuration Examples

#### With reasoning_effort="medium"

```yaml
model_list:
  - model_name: "gpt-5"
    litellm_params:
      model: "openai/gpt-5"
      api_base: "https://agentrouter.org/v1"
      api_key: "os.environ/OPENAI_API_KEY"
      reasoning_effort: "medium"

litellm_settings:
  drop_params: true
  set_verbose: true

general_settings:
  master_key: "sk-local-master"
```

#### With reasoning_effort="none"

```yaml
model_list:
  - model_name: "gpt-5"
    litellm_params:
      model: "openai/gpt-5"
      api_base: "https://agentrouter.org/v1"
      api_key: "os.environ/OPENAI_API_KEY"

litellm_settings:
  drop_params: true
  set_verbose: true

general_settings:
  master_key: "sk-local-master"
```

### Docker Usage with Reasoning

#### Using Environment Variables

```bash
# Add to .env file
echo "REASONING_EFFORT=medium" >> .env
docker-compose up -d
```

#### With docker-compose.yml Override

```yaml
services:
  litellm-proxy:
    environment:
      - REASONING_EFFORT=high
      - OPENAI_MODEL=gpt-5
      - OPENAI_BASE_URL=https://agentrouter.org/v1
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    # Note: Model alias is hardcoded as "gpt-5"
```

### Behavior and Compatibility

- **Precedence**: CLI arguments override environment variables
- **Default**: Uses `medium` when no reasoning effort is specified
- **Exclusion**: `none` value prevents the parameter from being included in generated config
- **Backward Compatible**: No impact when `REASONING_EFFORT` is not set
- **Config Files**: When using custom config files, reasoning effort is ignored (uses provided config)

## Docker Usage

### Docker Compose (Development)

The `docker-compose.yml` is configured for development with:

- **Live code reloading**: Changes to `src/` are reflected immediately
- **Environment file support**: Uses `.env` for configuration
- **Port mapping**: Exposes port 4000
- **Generated configuration**: Entrypoint writes `/app/generated-config.yaml` from environment variables

### Docker Compose (Multi-Model)

For multi-model deployments, update `docker-compose.yml` or use environment overrides:

```yaml
services:
  litellm-proxy:
    environment:
      - PROXY_MODEL_KEYS=gpt5,deepseek
      - MODEL_GPT5_ALIAS=gpt-5
      - MODEL_GPT5_UPSTREAM_MODEL=gpt-5
      - MODEL_GPT5_REASONING_EFFORT=medium
      - MODEL_DEEPSEEK_ALIAS=deepseek-v3.2
      - MODEL_DEEPSEEK_UPSTREAM_MODEL=deepseek-v3.2
      - MODEL_DEEPSEEK_REASONING_EFFORT=medium
      - OPENAI_API_BASE=https://agentrouter.org/v1
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY:-sk-local-master}
```

Or use environment file:

```bash
# Create multi-model .env
cat > .env << EOF
PROXY_MODEL_KEYS=gpt5,deepseek
MODEL_GPT5_ALIAS=gpt-5
MODEL_GPT5_UPSTREAM_MODEL=gpt-5
MODEL_DEEPSEEK_ALIAS=deepseek-v3.2
MODEL_DEEPSEEK_UPSTREAM_MODEL=deepseek-v3.2
OPENAI_API_KEY=sk-your-upstream-key
EOF

# Start with multi-model config
docker-compose up --build
```

### Docker Standalone

```bash
# Build the image
docker build -t litellm-launcher .

# Run with environment file
docker run --rm -p 4000:4000 \
  --env-file .env \
  litellm-launcher

# Run with custom config
docker run --rm -p 4000:4000 \
  --env-file .env \
  -v $(pwd)/config.yaml:/app/config.yaml \
  litellm-launcher --config /app/config.yaml

# Note: Dockerfile installs base deps from requirements.txt then the package in editable mode.
```

### Troubleshooting Docker Container

If you encounter authentication issues with the Docker container while the local demo script works:

1. **Quick test with curl** (from host):

   ```bash
   curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-sk-local-master}" \
     -d '{"model": "gpt-5", "messages": [{"role": "user", "content": "Hello!"}]}'
   ```
2. **Generated configuration**:
   The container writes `/app/generated-config.yaml` based on `.env` and CLI flags.
3. **Test the container**:

   ```bash
   curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer sk-local-master" \
     -d '{"model": "gpt-5", "messages": [{"role": "user", "content": "Hello!"}]}'
   ```

## Client Integration

Configure your OpenAI-compatible clients with:

```bash
OPENAI_API_KEY=sk-local-master
OPENAI_BASE_URL=http://localhost:4000
```

### Example with OpenAI Python Client

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

### Other SDKs

- **LangChain**: Use the same base URL and API key
- **LiteLLM**: Point to the local endpoint
- **Any OpenAI-compatible client**: Configure with the above settings


## Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests with coverage
pytest
```

### Code Structure

- `src/main.py`: Entry point and orchestration
- `src/cli.py`: Command-line interface and argument parsing
- `src/config.py`: Configuration file handling and validation
- `src/proxy.py`: LiteLLM proxy server management
- `src/telemetry.py`: Request telemetry logging middleware
- `src/utils.py`: Shared utilities (signal handling, dotenv loading, etc.)

The modular structure makes it easy to extend functionality and maintain clean separation of concerns.

## Request Telemetry Logging

The proxy automatically emits structured JSON logs for every chat completion request, providing visibility into model usage, latency, and error patterns. This telemetry is designed for observability, cost tracking, and performance monitoring.

### Enabled by Default

Telemetry logging is automatically enabled when the proxy starts with model specifications. No additional configuration is required.

### Log Format

Each chat completion request generates a single JSON log line with the following structure:

```json
{
  "event": "chat_completion",
  "timestamp": "2025-01-15T10:30:45.123456+00:00",
  "remote_addr": "192.168.1.100:54321",
  "path": "/v1/chat/completions",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 150.75,
  "streaming": false,
  "request_id": "chatcmpl-abc123",
  "model_alias": "gpt-5",
  "upstream_model": "openai/gpt-5",
  "prompt_tokens": 25,
  "completion_tokens": 40,
  "reasoning_tokens": 8,
  "total_tokens": 65,
  "error_type": null,
  "error_message": null,
  "client_request_id": "client-req-456"
}
```

### Field Descriptions

| Field | Description |
|--------|-------------|
| `event` | Always `"chat_completion"` for log filtering |
| `timestamp` | ISO-8601 timestamp with timezone |
| `remote_addr` | Client IP address (best effort) |
| `path` | Always `"/v1/chat/completions"` |
| `method` | Always `"POST"` |
| `status_code` | Final HTTP status code |
| `duration_ms` | End-to-end request duration in milliseconds |
| `streaming` | Boolean indicating if request was streaming |
| `request_id` | Response completion ID when available |
| `model_alias` | Model name from request (`model` field) |
| `upstream_model` | Resolved upstream model (`openai/...`) |
| `prompt_tokens` | Input token count when provided |
| `completion_tokens` | Output tokens (excluding reasoning) |
| `reasoning_tokens` | Reasoning tokens when supported |
| `total_tokens` | Total token usage when provided |
| `error_type` | Exception type on errors, `null` on success |
| `error_message` | Sanitized error message when errors occur |
| `client_request_id` | `X-Request-ID` header when provided |

### Special Cases

#### Missing Usage Data

When providers don't return usage metadata:

```json
{
  "prompt_tokens": null,
  "completion_tokens": null,
  "reasoning_tokens": null,
  "total_tokens": null,
  "missing_usage": true
}
```

#### Error Responses

When requests fail:

```json
{
  "status_code": 429,
  "error_type": "RateLimitError",
  "error_message": "Rate limit exceeded",
  "prompt_tokens": null,
  "completion_tokens": null,
  "total_tokens": null
}
```

#### Parse Errors

When response parsing fails:

```json
{
  "parse_error": true,
  "prompt_tokens": null,
  "completion_tokens": null,
  "total_tokens": null
}
```

### Integration Examples

#### CloudWatch Logs

```bash
# Collect logs with jq filtering
curl localhost:4000/v1/chat/completions ... | \
  jq -c '. | select(.event == "chat_completion")' >> cloudwatch-logs.json
```

#### Loki/Prometheus

```yaml
# Grafana Loki log parsing rules
- match:
    selector: '{app="litellm-proxy"}'
    stages:
      - json:
          expressions:
            duration: duration_ms
            status: status_code
            model: model_alias
      - regex:
          expression: '(?P<level>\w+)'
```

#### Cost Attribution

```python
# Calculate per-model costs from logs
import json

def calculate_costs(log_file_path, cost_per_token):
    model_costs = {}

    with open(log_file_path) as f:
        for line in f:
            log = json.loads(line)
            if log.get('event') != 'chat_completion':
                continue

            model = log['model_alias']
            total_tokens = log.get('total_tokens', 0)

            if total_tokens is not None:
                cost = total_tokens * cost_per_token
                model_costs[model] = model_costs.get(model, 0) + cost

    return model_costs
```

### Performance Impact

- **Overhead**: <5ms per request under typical load
- **Thread Safety**: Safe with multiple workers (`--num_workers`)
- **Failure Resilience**: Logging failures don't affect request processing

### Logger Configuration

Telemetry uses the `litellm_launcher.telemetry` logger at INFO level:

```python
import logging

# Custom configuration
logging.getLogger("litellm_launcher.telemetry").setLevel(logging.DEBUG)

# Custom handler
handler = logging.FileHandler("telemetry.log")
logging.getLogger("litellm_launcher.telemetry").addHandler(handler)
```

### Disabling Telemetry

To disable telemetry logging, use a custom LiteLLM config file instead of auto-generated configuration:

```bash
# Start with custom config (no telemetry)
python -m src.main --config /path/to/custom-config.yaml
```
