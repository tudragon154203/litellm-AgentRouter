FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install LiteLLM with proxy dependencies
RUN pip install --no-cache-dir "litellm[proxy]"

COPY local_openai_proxy.py /app/local_openai_proxy.py
COPY .env /app/.env

EXPOSE 4000
ENV LITELLM_HOST=0.0.0.0 \
    LITELLM_PORT=4000 \
    LITELLM_MODEL_ALIAS=local-gpt \
    OPENAI_MODEL=openai/gpt-4o \
    OPENAI_BASE_URL=https://api.openai.com/v1 \
    UPSTREAM_API_KEY_ENV=OPENAI_API_KEY \
    LITELLM_MASTER_KEY=sk-local-master \
    LITELLM_DROP_PARAMS=true

ENTRYPOINT ["python", "/app/local_openai_proxy.py"]
