#!/usr/bin/env python3
from __future__ import annotations

import pytest

from src.config.rendering import render_config


class TestRenderingBranches:
    """Test uncovered branches in config rendering."""

    def test_render_config_empty_model_specs(self):
        """render_config should raise ValueError for empty model specs."""
        with pytest.raises(ValueError, match="No model specifications provided"):
            render_config(
                model_specs=[],
                global_upstream_base="https://api.openai.com/v1",
                global_upstream_key_env="OPENAI_API_KEY",
                master_key="sk-test",
                drop_params=False,
                streaming=True
            )

    def test_render_config_none_model_specs(self):
        """render_config should raise ValueError for None model specs."""
        with pytest.raises(ValueError, match="No model specifications provided"):
            render_config(
                model_specs=None,
                global_upstream_base="https://api.openai.com/v1",
                global_upstream_key_env="OPENAI_API_KEY",
                master_key="sk-test",
                drop_params=False,
                streaming=True
            )
