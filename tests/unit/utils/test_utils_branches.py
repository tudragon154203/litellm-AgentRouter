#!/usr/bin/env python3
from __future__ import annotations

import os

from src.utils import validate_prereqs


class TestUtilsBranches:
    """Test uncovered branches in utils module."""

    def test_validate_prereqs_skip_check(self):
        """validate_prereqs should skip check if SKIP_PREREQ_CHECK is set."""
        original = os.environ.get("SKIP_PREREQ_CHECK")
        try:
            os.environ["SKIP_PREREQ_CHECK"] = "1"
            
            # Should not raise even if imports would fail
            validate_prereqs()
            
        finally:
            if original is not None:
                os.environ["SKIP_PREREQ_CHECK"] = original
            else:
                os.environ.pop("SKIP_PREREQ_CHECK", None)

    def test_validate_prereqs_normal_check(self):
        """validate_prereqs should check imports normally."""
        original = os.environ.get("SKIP_PREREQ_CHECK")
        try:
            os.environ.pop("SKIP_PREREQ_CHECK", None)
            
            # Should succeed with litellm installed
            validate_prereqs()
            
        finally:
            if original is not None:
                os.environ["SKIP_PREREQ_CHECK"] = original
