#!/bin/bash
# Entrypoint script that generates config from .env and starts the service

set -e

echo "Starting LiteLLM proxy with configuration from environment variables..."

# Start with basic config structure
cat > /app/generated-config.yaml << EOF
model_list:
EOF

# Helper function to add model to config
add_model() {
    local alias="$1"
    local upstream_model="$2"
    local reasoning_effort="$3"

    cat >> /app/generated-config.yaml << EOF
  - model_name: "${alias}"
    litellm_params:
      model: "openai/${upstream_model}"
      api_base: "${OPENAI_BASE_URL:-https://agentrouter.org/v1}"
      api_key: "${OPENAI_API_KEY}"
      custom_llm_provider: "openai"
      headers:
        "User-Agent": "QwenCode/0.0.14 (win32; unknown)"
        "Content-Type": "application/json"
EOF

    # Add reasoning_effort parameter if specified and not "none"
    if [[ -n "${reasoning_effort}" && "${reasoning_effort}" != "none" ]]; then
      echo "      reasoning_effort: \"${reasoning_effort}\"" >> /app/generated-config.yaml
    fi
}

# Add models based on configuration
if [[ -n "${MODEL_GPT5_ALIAS}" ]]; then
    add_model "${MODEL_GPT5_ALIAS}" "${MODEL_GPT5_UPSTREAM_MODEL:-gpt-5}" "${MODEL_GPT5_REASONING_EFFORT:-none}"
fi

if [[ -n "${MODEL_DEEPSEEK_ALIAS}" ]]; then
    add_model "${MODEL_DEEPSEEK_ALIAS}" "${MODEL_DEEPSEEK_UPSTREAM_MODEL:-deepseek-v3.2}" "${MODEL_DEEPSEEK_REASONING_EFFORT:-none}"
fi

if [[ -n "${MODEL_GLM_ALIAS}" ]]; then
    add_model "${MODEL_GLM_ALIAS}" "${MODEL_GLM_UPSTREAM_MODEL:-glm-4.6}" "${MODEL_GLM_REASONING_EFFORT:-none}"
fi

# Add shared configuration
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