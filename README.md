# LiteLLM Local Gateway

This directory contains a small utility script and Docker image that launch a
LiteLLM proxy exposing an OpenAI-compatible API endpoint. The proxy is useful
when other local services expect the OpenAI client interface but you want to
fan traffic out to any provider supported by LiteLLM.

## Prerequisites

- Python 3.10+
- `pip install 'litellm[proxy]'` (includes FastAPI, uvicorn, and optional proxy dependencies)

## Quick start (host)

1. Review `litellm/.env` (pre-populated with the hard-coded values from the original `minimal-litellm-test.py`) or adjust it to match your own upstream service. The script reads the standard OpenAI-style variables:

   ```
   OPENAI_API_KEY=…
   OPENAI_BASE_URL=…
   OPENAI_MODEL=…
   ```

2. Start the proxy:

   ```bash
   python litellm/local_openai_proxy.py
   ```

The server listens on `http://0.0.0.0:4000` by default and enforces the
`Authorization: Bearer sk-local-master` master key. Point OpenAI-compatible
clients at `http://localhost:4000/v1` with that key.

Override behaviour with CLI flags or environment variables (see
`python litellm/local_openai_proxy.py --help`). The script can also print the
generated config:

```bash
python litellm/local_openai_proxy.py --print-config
```

To use a custom LiteLLM configuration, create `litellm/config.yaml` with your
model mappings and start the proxy with:

```bash
python litellm/local_openai_proxy.py --config litellm/config.yaml
```

## Docker usage

```
docker build -t litellm-local litellm
docker run --rm -p 4000:4000 \
  --env-file litellm/.env \
  litellm-local
```

Mount a custom config if required:

```
docker run --rm -p 4000:4000 \
  --env-file litellm/.env \
  -v $(pwd)/my-config.yaml:/app/config.yaml \
  litellm-local --config /app/config.yaml
```

The container entrypoint is the same script, so any CLI options are accepted
after the image name.

## Integrating clients

Configure your OpenAI-compatible clients with:

```
OPENAI_API_KEY=sk-local-master
OPENAI_BASE_URL=http://localhost:4000
```

Other SDKs (LangChain, LiteLLM `completion`, etc.) can point to the same local
endpoint.
