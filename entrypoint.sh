#!/bin/bash
# Entrypoint script that generates config from .env and starts the service.
# Uses Python-based config generation for multi-upstream support.

set -e

echo "Starting LiteLLM proxy with configuration from environment variables..."

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

# Generate config using Python (supports multi-upstream)
CONFIG_PATH="/app/generated-config.yaml"
echo "Generating configuration..."
python -m src.main --print-config > "${CONFIG_PATH}"

echo "Generated config:"
sed -e 's/\(api_key: "\)[^"]*/\1***MASKED***"/' \
    -e 's/\(api_key: os.environ\/\)\([^"]*\)/api_key: os.environ\/***MASKED***/' \
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
