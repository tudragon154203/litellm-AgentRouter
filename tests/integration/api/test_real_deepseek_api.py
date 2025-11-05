#!/usr/bin/env python3
"""Real integration tests that make actual DeepSeek v3.2 API calls via litellm."""

from __future__ import annotations

import os
import sys

import pytest

from src.config.config import runtime_config

litellm = pytest.importorskip("litellm")


class TestRealDeepSeekAPI:
    @classmethod
    def setup_class(cls):
        runtime_config.ensure_loaded()
        cls.api_key = runtime_config.get_str("OPENAI_API_KEY")
        cls.base_url = runtime_config.get_str("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        if not cls.api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")
        litellm.drop_params = True

    def _call_deepseek_not_stream(self, **kwargs):
        if 'stream' in kwargs:
            del kwargs['stream']
        params = {
            'model': 'openai/deepseek-v3.2',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': False,
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": f"QwenCode/0.0.14 ({sys.platform}; {os.getenv('PROCESSOR_ARCHITECTURE', 'unknown')})"
            }
        }
        params.update(kwargs)
        return litellm.completion(**params)

    def _call_deepseek_stream(self, **kwargs):
        params = {
            'model': 'openai/deepseek-v3.2',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': True,
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": f"QwenCode/0.0.14 ({sys.platform}; {os.getenv('PROCESSOR_ARCHITECTURE', 'unknown')})"
            }
        }
        params.update(kwargs)
        return litellm.completion(**params)

    def test_deepseek_basic_completion(self):
        resp = self._call_deepseek_not_stream(
            messages=[{"role": "user", "content": "Say hi in one short sentence."}],
            max_tokens=200,
            temperature=0.7,
        )
        assert resp is not None
        assert hasattr(resp, 'choices') and len(resp.choices) > 0
        msg = resp.choices[0].message
        assert msg and getattr(msg, 'content', None)
        assert msg.content.strip()
        assert hasattr(resp, 'usage') and resp.usage and resp.usage.total_tokens > 0

    def test_deepseek_streaming_completion(self):
        stream = self._call_deepseek_stream(
            messages=[{"role": "user", "content": "List 3 colors."}],
            max_tokens=100,
            temperature=0.7,
        )
        assert hasattr(stream, '__iter__')
        parts = []
        chunks = 0
        for ch in stream:
            chunks += 1
            assert hasattr(ch, 'choices') and len(ch.choices) > 0
            delta = ch.choices[0].delta
            if delta and getattr(delta, 'content', None):
                parts.append(delta.content)
        assert chunks > 0
        assert ''.join(parts).strip()
