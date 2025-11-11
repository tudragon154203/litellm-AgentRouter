#!/usr/bin/env python3
"""Real integration tests that make actual GLM 4.6 API calls via litellm."""

from __future__ import annotations
from src.config.config import runtime_config

import pytest

from src.utils import build_user_agent

litellm = pytest.importorskip("litellm")


class TestRealGLMAPI:
    @classmethod
    def setup_class(cls):
        runtime_config.ensure_loaded()
        cls.api_key = runtime_config.get_str("OPENAI_API_KEY")
        cls.base_url = runtime_config.get_str("OPENAI_BASE_URL", "https://agentrouter.org/v1")
        cls.use_node_proxy = runtime_config.get_bool("NODE_UPSTREAM_PROXY_ENABLE", False)

        if not cls.api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")

        # If Node proxy is enabled, route through localhost
        # The actual Node proxy is started by the session-scoped fixture
        if cls.use_node_proxy:
            cls.base_url = "http://127.0.0.1:4000/v1"

        litellm.drop_params = True

    def _call_glm_not_stream(self, **kwargs):
        if 'stream' in kwargs:
            del kwargs['stream']
        params = {
            'model': 'openai/glm-4.6',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': False,
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": build_user_agent()
            }
        }
        params.update(kwargs)
        return litellm.completion(**params)

    def _call_glm_stream(self, **kwargs):
        params = {
            'model': 'openai/glm-4.6',
            'api_base': self.base_url,
            'api_key': self.api_key,
            'custom_llm_provider': 'openai',
            'stream': True,
            'headers': {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": build_user_agent()
            }
        }
        params.update(kwargs)
        return litellm.completion(**params)

    def test_glm_basic_completion(self):
        resp = self._call_glm_not_stream(
            messages=[{"role": "user", "content": "Say hi in one short sentence."}],
            max_tokens=200,
            temperature=0.7,
        )
        assert resp is not None
        assert hasattr(resp, 'choices') and len(resp.choices) > 0
        msg = resp.choices[0].message
        assert msg is not None

        # GLM might return content or reasoning_content
        content = getattr(msg, 'content', None) or getattr(msg, 'reasoning_content', None)
        assert content and content.strip()
        assert hasattr(resp, 'usage') and resp.usage and resp.usage.total_tokens > 0

    def test_glm_chinese_text(self):
        """Test GLM's Chinese language capabilities."""
        resp = self._call_glm_not_stream(
            messages=[{"role": "user", "content": "用中文回答：什么是人工智能？"}],
            max_tokens=100,
            temperature=0.7,
        )
        msg = resp.choices[0].message
        content = (getattr(msg, 'content', None) or getattr(msg, 'reasoning_content', None) or "").strip()
        assert content
        assert any(char in content for char in "人工智能是")  # Should contain Chinese characters

    def test_glm_streaming_completion(self):
        stream = self._call_glm_stream(
            messages=[{"role": "user", "content": "List 4 programming languages."}],
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
            if delta:
                content = getattr(delta, 'content', None) or getattr(delta, 'reasoning_content', None)
                if content:
                    parts.append(content)
        assert chunks > 0
        assert ''.join(parts).strip()
