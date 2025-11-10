#!/usr/bin/env python3
"""Shared fixtures for API integration tests."""

from __future__ import annotations

import pytest
import time

from src.config.config import runtime_config
from src.node.process import NodeProxyProcess


@pytest.fixture(scope="session")
def node_proxy_for_tests():
    """
    Session-scoped fixture that starts a single Node proxy instance
    for all API integration tests to share.
    """
    runtime_config.ensure_loaded()
    use_node_proxy = runtime_config.get_bool("NODE_UPSTREAM_PROXY_ENABLE", False)
    
    if not use_node_proxy:
        yield None
        return
    
    api_key = runtime_config.get_str("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")
    
    proxy = None
    try:
        proxy = NodeProxyProcess()
        proxy.start()
        # Give Node proxy time to start and bind port
        time.sleep(2)
        
        if not proxy.is_running:
            pytest.skip("Failed to start Node proxy")
        
        yield proxy
    except Exception as e:
        pytest.skip(f"Failed to start Node proxy: {e}")
    finally:
        if proxy:
            proxy.stop()
