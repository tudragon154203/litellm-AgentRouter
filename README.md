# LiteLLM Local Gateway

A modular LiteLLM proxy launcher that exposes an OpenAI-compatible API endpoint. The proxy is useful when other local services expect the OpenAI client interface but you want to fan traffic out to any provider supported by LiteLLM.

## Project Structure

```
├── src/
│   ├── main.py          # Main entry point
│   ├── cli.py           # CLI argument parsing
│   ├── config.py        # Configuration management
│   ├── proxy.py         # Proxy server logic
│   └── utils.py         # Utility functions
├── demo/
│   └── minimal-litellm-test.py  # Working demo script
├── docker-compose.yml   # Docker Compose configuration
├── debug-config.yaml    # Fixed configuration for Docker container
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

The server will start on `http://localhost:4000` with live code reloading for development.

### Working Demo

A minimal working example is available in `demo/minimal-litellm-test.py`:

```bash
# Test the local LiteLLM setup directly
python demo/minimal-litellm-test.py
```

This script demonstrates the exact configuration that works with your OpenAI-compatible endpoint.

### Local Development

1. Install the package and dependencies:

   ```bash
   pip install -e .
   ```

2. Configure your environment variables (see `.env.example`)

3. Run the proxy:

   ```bash
   python -m src.main
   ```

## Configuration

The proxy reads configuration from environment variables. Key settings include:

- **LITELLM_HOST**: Host interface (default: 0.0.0.0)
- **LITELLM_PORT**: Port number (default: 4000)
- **LITELLM_MODEL_ALIAS**: Public model name (default: gpt-5)
- **LITELLM_MASTER_KEY**: Master key for authentication (default: sk-local-master)
- **OPENAI_MODEL**: Upstream model (default: gpt-5)
- **OPENAI_BASE_URL**: Upstream API base URL (default: https://api.openai.com/v1)
- **OPENAI_API_KEY**: Your OpenAI API key

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

## Docker Usage

### Docker Compose (Development)

The `docker-compose.yml` is configured for development with:
- **Live code reloading**: Changes to `src/` are reflected immediately
- **Environment file support**: Uses `.env` for configuration
- **Port mapping**: Exposes port 4000
- **Fixed configuration**: Uses `debug-config.yaml` for reliable OpenAI-compatible endpoint support

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
```

### Troubleshooting Docker Container

If you encounter authentication issues with the Docker container while the local demo script works:

1. **Check the demo script**:
   ```bash
   python demo/minimal-litellm-test.py
   ```

2. **Use the fixed configuration**:
   The container includes `debug-config.yaml` with the working configuration that matches the demo script.

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
- `src/utils.py`: Shared utilities (signal handling, dotenv loading, etc.)

The modular structure makes it easy to extend functionality and maintain clean separation of concerns.
