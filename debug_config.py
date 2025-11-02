#!/usr/bin/env python3
"""Debug script to see what config is generated."""

import os
import sys

# Add src to path
sys.path.insert(0, '/app/src')

from src.config.parsing import load_model_specs_from_env, prepare_config
from src.cli import parse_args

# Load environment as container would
for key, value in os.environ.items():
    if 'MODEL' in key or 'OPENAI' in key:
        print(f"{key}={value}")

print("\n" + "="*50)
print("Loading model specs from environment...")
try:
    model_specs = load_model_specs_from_env()
    print(f"Found {len(model_specs)} model specs:")
    for spec in model_specs:
        print(f"  - {spec.key}: alias={spec.alias}, upstream={spec.upstream_model}, key_env={spec.upstream_key_env}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50)
print("Simulating CLI args...")
args = parse_args(['--host', '0.0.0.0', '--port', '4000'])
print(f"Global upstream_key_env: {getattr(args, 'upstream_key_env', None)}")

print("\n" + "="*50)
print("Preparing config...")
try:
    config_path_or_text, is_generated = prepare_config(args)
    print(f"Config is_generated: {is_generated}")
    if is_generated:
        print("Generated config text:")
        print(config_path_or_text)
    else:
        print(f"Config file: {config_path_or_text}")
except Exception as e:
    print(f"Error preparing config: {e}")