#!/bin/bash
# Entrypoint script that generates config from .env and starts the service, using PRD 3 schema.

set -e

echo "Starting LiteLLM proxy with configuration from environment variables..."

# Align LiteLLM user agent with the current runtime platform (matches demo scripts).
USER_AGENT="$(python - <<'PY'
from src.utils import build_user_agent

print(build_user_agent(), end="")
PY
)"

# Reject legacy alias variables
for var in $(env | grep -E "MODEL_.*_ALIAS=" | cut -d= -f1); do
    echo "ERROR: Legacy environment variable '$var' detected."
    echo "Please remove all MODEL_*_ALIAS variables and use only MODEL_*_UPSTREAM_MODEL."
    echo "The alias will be automatically derived from the upstream model name."
    exit 1
done

if [[ -z "${PROXY_MODEL_KEYS:-}" ]]; then
    echo "ERROR: PROXY_MODEL_KEYS must be set (comma-separated logical keys)."
    exit 1
fi

CONFIG_PATH="/app/generated-config.yaml"
cat > "${CONFIG_PATH}" << 'EOF'
model_list:
EOF

IFS=',' read -ra RAW_KEYS <<< "${PROXY_MODEL_KEYS}"

derive_alias() {
    local upstream="$1"
    python - "$upstream" <<'PY'
import sys

upstream = sys.argv[1]
for prefix in ("openai/", "anthropic/", "google/", "azure/"):
    if upstream.startswith(prefix):
        print(upstream[len(prefix):])
        break
else:
    print(upstream)
PY
}

for raw_key in "${RAW_KEYS[@]}"; do
    trimmed="$(echo "${raw_key}" | tr -d '[:space:]')"
    if [[ -z "${trimmed}" ]]; then
        continue
    fi
    upper_key="$(echo "${trimmed}" | tr '[:lower:]' '[:upper:]')"
    prefix="MODEL_${upper_key}_"

    upstream_var="${prefix}UPSTREAM_MODEL"
    upstream_model="${!upstream_var}"
    if [[ -z "${upstream_model}" ]]; then
        echo "ERROR: Missing environment variable: ${upstream_var}"
        exit 1
    fi

    alias="$(derive_alias "${upstream_model}")"
    if [[ -z "${alias}" ]]; then
        echo "ERROR: Unable to derive alias for upstream model '${upstream_model}'."
        exit 1
    fi

    reasoning_var="${prefix}REASONING_EFFORT"
    reasoning_effort="${!reasoning_var}"

    if [[ "${upstream_model}" != openai/* ]]; then
        model_line="openai/${upstream_model}"
    else
        model_line="${upstream_model}"
    fi

    cat >> "${CONFIG_PATH}" << EOF
  - model_name: "${alias}"
    litellm_params:
      model: "${model_line}"
      api_base: "${OPENAI_BASE_URL:-https://agentrouter.org/v1}"
      api_key: "${OPENAI_API_KEY}"
      custom_llm_provider: "openai"
      headers:
        "User-Agent": "${USER_AGENT}"
        "Content-Type": "application/json"
EOF

    if [[ -n "${reasoning_effort}" && "${reasoning_effort}" != "none" ]]; then
        echo "      reasoning_effort: \"${reasoning_effort}\"" >> "${CONFIG_PATH}"
    fi
done

cat >> "${CONFIG_PATH}" << EOF

litellm_settings:
  drop_params: true
  set_verbose: false

# Default completion parameters (can be overridden per-request)
completion_params:
  max_tokens: ${MAX_TOKENS:-8192}

general_settings:
  master_key: "${LITELLM_MASTER_KEY:-sk-local-master}"
EOF

echo "Generated config:"
sed -e 's/\(api_key: "\)[^"]*/\1***MASKED***"/' \
    -e 's/\(master_key: "\)[^"]*/\1***MASKED***"/' \
    "${CONFIG_PATH}"
echo ""
ls -la "${CONFIG_PATH}"
echo "--- CONFIG FILE END ---"

# Bind inside the container to a fixed internal port to avoid mismatch with published host port.
# docker-compose maps host ${PORT:-4000} -> container 4000 (see docker-compose.yml:5),
# so the service must always listen on 4000 internally regardless of host PORT overrides.
HOST="${LITELLM_HOST:-0.0.0.0}"
HOST_PORT="${PORT:-4000}"
CONTAINER_PORT=4000

echo "Container listening on port ${CONTAINER_PORT}; host publishes ${HOST_PORT} -> ${CONTAINER_PORT}"

exec python -m src.main --config "${CONFIG_PATH}" --host "${HOST}" --port "${CONTAINER_PORT}"
