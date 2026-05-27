"""Phase 18: Tests for the offline shadow pipeline verification script.

5+ tests covering the verification functions.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FIXTURE_DIR = str(_REPO_ROOT / "tests" / "fixtures" / "offline_shadow_research")


class TestVerificationImports:
    def test_script_importable(self):
        spec = __import__(
            "scripts.verify_offline_shadow_research_pipeline",
            fromlist=["main"],
        )
        assert hasattr(spec, "main")

    def test_check_imports_passes(self):
        from scripts.verify_offline_shadow_research_pipeline import _check_imports
        errors = _check_imports()
        assert errors == []

    def test_check_fixtures_passes(self):
        from scripts.verify_offline_shadow_research_pipeline import _check_fixtures
        errors = _check_fixtures()
        assert errors == []

    def test_check_pipeline_e2e_passes(self):
        from scripts.verify_offline_shadow_research_pipeline import _check_pipeline_e2e
        errors = _check_pipeline_e2e()
        assert errors == []


class TestVerificationMain:
    def test_main_returns_zero(self):
        from scripts.verify_offline_shadow_research_pipeline import main
        # main() runs tests which takes time, but should return 0
        # We just verify it's callable and returns int
        result = main()
        assert result == 0
