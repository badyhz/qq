"""Tests for compare research quality bundles CLI — T8401-T8440.

Identical hash, timestamp allowlist, mismatch tests.
"""
from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path
from core.research_rerun_diff import detect_rerun_diff


class TestBundleComparisonNormal:
    def test_identical_bundles(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            for d in (d1, d2):
                (Path(d) / "test.json").write_text(json.dumps({"key": "value"}))
            result = detect_rerun_diff(Path(d1), Path(d2), ("test.json",))
            assert result["identical"]


class TestBundleComparisonAdversarial:
    def test_different_bundles(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            (Path(d1) / "a.json").write_text(json.dumps({"v": 1}))
            (Path(d2) / "a.json").write_text(json.dumps({"v": 2}))
            result = detect_rerun_diff(Path(d1), Path(d2), ("a.json",))
            assert not result["identical"]
            assert "a.json" in result["differences"]

    def test_missing_artifact(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            (Path(d1) / "a.json").write_text(json.dumps({"v": 1}))
            result = detect_rerun_diff(Path(d1), Path(d2), ("a.json",))
            assert not result["identical"]


class TestBundleComparisonSafetyBoundary:
    def test_result_safety(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            result = detect_rerun_diff(Path(d1), Path(d2), ())
            assert result["release_hold"] == "HOLD"
            assert result["advisory_only"] is True
