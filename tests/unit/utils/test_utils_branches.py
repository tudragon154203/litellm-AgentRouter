#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

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

            completion = subprocess.CompletedProcess(["node", "--version"], 0)
            with patch("shutil.which", return_value="/usr/bin/node"), \
                    patch("src.utils.subprocess.run", return_value=completion) as mock_run:
                validate_prereqs()
                mock_run.assert_called_once()

        finally:
            if original is not None:
                os.environ["SKIP_PREREQ_CHECK"] = original
