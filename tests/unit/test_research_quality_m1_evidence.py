"""Tests for M1 evidence — T5271-T5280.

Evidence artifact shape tests.
"""
from __future__ import annotations

import pytest
from core.research_quality_contract import DEFAULT_CONTRACT
from core.research_quality_manifest import REQUIRED_ARTIFACTS
from core.research_fixture_contract import FIXTURE_CLASSES
from core.research_safety_regression import build_safety_report
from core.research_reproducibility_seed import DEFAULT_SEED
from core.research_quality_bundle import write_bundle_skeleton


class TestM1Evidence:
    def test_contract_valid(self):
        assert DEFAULT_CONTRACT.is_valid()

    def test_manifest_has_all_artifacts(self):
        assert len(REQUIRED_ARTIFACTS) >= 25

    def test_fixture_classes_exist(self):
        assert len(FIXTURE_CLASSES) == 6

    def test_safety_report_passes(self):
        r = build_safety_report()
        assert r.verdict == "PASS"

    def test_default_seed(self):
        assert DEFAULT_SEED == 424242

    def test_bundle_skeleton_safety(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            write_bundle_skeleton(Path(d), seed=42)
            import json
            m = json.loads((Path(d) / "manifest.json").read_text())
            assert m["release_hold"] == "HOLD"
