#!/bin/bash
# Entrypoint script that generates config from .env and starts the service

set -e

echo "Starting LiteLLM proxy with configuration from environment variables..."

# Generate config directly to match original debug-config.yaml format
# Include reasoning_effort if specified and not "none"
cat > /app/generated-config.yaml << EOF
model_list:
  - model_name: "gpt-5"
    litellm_params:
      model: "${OPENAI_MODEL:-gpt-5}"
      api_base: "${OPENAI_BASE_URL:-https://api.openai.com/v1}"
      api_key: "${OPENAI_API_KEY}"
      custom_llm_provider: "openai"
      headers:
        "User-Agent": "QwenCode/0.0.14 (win32; unknown)"
        "Content-Type": "application/json"
EOF

# Add reasoning_effort parameter if specified and not "none"
if [[ -n "${REASONING_EFFORT}" && "${REASONING_EFFORT}" != "none" ]]; then
  echo "      reasoning_effort: \"${REASONING_EFFORT}\"" >> /app/generated-config.yaml
fi

cat >> /app/generated-config.yaml << EOF

litellm_settings:
  drop_params: true

# Default completion parameters (can be overridden per-request)
completion_params:
  max_tokens: ${MAX_TOKENS:-8192}

general_settings:
  master_key: "${LITELLM_MASTER_KEY:-sk-local-master}"
EOF

echo "Generated config:"
# Mask the API key for security in logs
sed 's/\(api_key: "\)[^"]*/\1***MASKED***"/' /app/generated-config.yaml
echo ""

# Start the proxy with the generated config
exec python -m src.main --config /app/generated-config.yaml --host "0.0.0.0" --port "${PORT:-4000}"