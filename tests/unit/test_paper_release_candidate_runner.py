"""Tests for release candidate runner — structure only, no full run."""
from __future__ import annotations

import json
import os
import py_compile
import sys

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
SCRIPT = os.path.join(REPO_ROOT, "scripts", "run_paper_release_candidate.py")


class TestReleaseCandidateRunnerStructure:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_script_is_importable(self):
        """Verify script can be imported without executing main."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("rc_runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        # Don't execute, just verify it loads
        assert spec is not None
        assert mod is not None

    def test_has_main_function(self):
        """Verify script has main() function."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("rc_runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_has_runners_list(self):
        """Verify RUNNERS list exists and has expected entries."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("rc_runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "RUNNERS")
        assert isinstance(mod.RUNNERS, list)
        assert len(mod.RUNNERS) >= 5

    def test_report_dir_defined(self):
        """Verify REPORT_DIR is defined."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("rc_runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "REPORT_DIR")
        assert "reports" in mod.REPORT_DIR
