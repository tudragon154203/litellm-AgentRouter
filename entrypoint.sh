#!/bin/bash
# Simplified entrypoint wrapper that delegates to Python entrypoint module

exec python -m src.config.entrypoint "$@"
