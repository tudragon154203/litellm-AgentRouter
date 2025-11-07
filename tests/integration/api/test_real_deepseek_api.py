#!/usr/bin/env python3
"""Real integration tests that make actual DeepSeek v3.2 API calls via litellm."""

from __future__ import annotations

from tests.integration.api.base_model_test import BaseModelTest, ModelConfig


class TestRealDeepSeekAPI(BaseModelTest):
    """Integration tests that make real DeepSeek v3.2 API calls."""

    model_config = ModelConfig(
        model_name='openai/deepseek-v3.2',
        api_key_env='OPENAI_API_KEY',
        base_url_env='OPENAI_BASE_URL',
        default_base_url='https://agentrouter.org/v1',
    )
