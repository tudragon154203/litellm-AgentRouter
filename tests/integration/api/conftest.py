#!/usr/bin/env python3
"""Shared fixtures for API integration tests."""

from __future__ import annotations

import pytest
import time
import socket
import os
from pathlib import Path
from filelock import FileLock

from src.config.config import runtime_config
from src.node.process import NodeProxyProcess


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


@pytest.fixture(scope="session", autouse=True)
def node_proxy_for_tests(tmp_path_factory):
    """
    Session-scoped fixture that starts a single Node proxy instance
    for all API integration tests to share across parallel workers.
    
    Uses file locking to ensure only one worker starts the Node proxy.
    """
    runtime_config.ensure_loaded()
    use_node_proxy = runtime_config.get_bool("NODE_UPSTREAM_PROXY_ENABLE", False)
    
    if not use_node_proxy:
        yield None
        return
    
    api_key = runtime_config.get_str("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")
    
    # Use a lock file to coordinate between parallel workers
    root_tmp_dir = tmp_path_factory.getbasetemp().parent
    lock_file = root_tmp_dir / "node_proxy.lock"
    
    with FileLock(str(lock_file)):
        # Check if Node proxy is already running (started by another worker)
        if is_port_in_use(4000):
            # Another worker already started it, just wait a bit and use it
            time.sleep(0.5)
            yield None
            return
        
        # This worker will start the Node proxy
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
            # Only stop if this worker started it
            if proxy:
                proxy.stop()
                # Give it time to fully stop
                time.sleep(1)
