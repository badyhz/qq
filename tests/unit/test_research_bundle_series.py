"""Tests for research bundle series loader.

Program A tests. Offline only. No network.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.research_bundle_series import (
    BundleRecord,
    build_bundle_series_index,
    load_bundle_series,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_comparison_analytics"


class TestBundleSeriesLoader:
    """Test bundle series loading."""

    def test_load_two_bundles(self):
        """Test loading 2 bundles succeeds."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        assert len(records) == 2
        assert records[0].label in ("baseline", "candidate")
        assert records[1].label in ("baseline", "candidate")

    def test_load_rejects_one_bundle(self):
        """Test loading 1 bundle raises ValueError."""
        bundles = [("only", FIXTURES / "artifact_browser_baseline")]
        with pytest.raises(ValueError, match="at least 2"):
            load_bundle_series(bundles)

    def test_deterministic_ordering(self):
        """Test bundles are sorted by label."""
        bundles = [
            ("zulu", FIXTURES / "artifact_browser_baseline"),
            ("alpha", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles, strict=False)
        assert records[0].label == "alpha"
        assert records[1].label == "zulu"

    def test_safety_valid_pass(self):
        """Test safety validation passes for valid bundles."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        assert all(r.safety_valid for r in records)

    def test_safety_invalid_fails_strict(self):
        """Test safety invalid bundle fails in strict mode."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("invalid", FIXTURES / "artifact_browser_invalid_safety"),
        ]
        with pytest.raises(ValueError, match="Bundle validation failed"):
            load_bundle_series(bundles, strict=True)

    def test_safety_invalid_non_strict(self):
        """Test safety invalid bundle passes in non-strict mode."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("invalid", FIXTURES / "artifact_browser_invalid_safety"),
        ]
        records = load_bundle_series(bundles, strict=False)
        assert len(records) == 2
        invalid = [r for r in records if r.label == "invalid"][0]
        assert not invalid.safety_valid

    def test_missing_directory(self):
        """Test missing bundle directory fails."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("missing", Path("/nonexistent/bundle")),
        ]
        with pytest.raises(ValueError):
            load_bundle_series(bundles, strict=True)

    def test_corrupted_json_fails_strict(self):
        """Test corrupted JSON fails in strict mode."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("corrupted", FIXTURES / "artifact_browser_corrupted"),
        ]
        with pytest.raises(ValueError, match="corrupted JSON|parse error"):
            load_bundle_series(bundles, strict=True)

    def test_artifact_hashes_present(self):
        """Test artifact hashes are computed."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        for r in records:
            assert isinstance(r.artifact_hashes, dict)
            assert len(r.artifact_hashes) > 0

    def test_manifest_loaded(self):
        """Test manifest is loaded from bundle."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        for r in records:
            assert r.manifest.get("release_hold") == "HOLD"

    def test_build_series_index(self):
        """Test bundle series index creation."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        index = build_bundle_series_index(records)
        assert index["bundle_count"] == 2
        assert index["all_safety_valid"] is True
        assert index["schema_version"] == "1.0.0"


class TestBundleSeriesNegative:
    """Negative/adversarial tests for bundle series."""

    def test_zero_bundles(self):
        """Test zero bundles raises."""
        with pytest.raises(ValueError):
            load_bundle_series([])

    def test_release_hold_mismatch(self):
        """Test release_hold mismatch fails in strict mode."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        with pytest.raises(ValueError):
            load_bundle_series(bundles, strict=True, release_hold="RELEASED")

    def test_bundle_record_to_dict(self):
        """Test BundleRecord serialization."""
        bundles = [
            ("a", FIXTURES / "artifact_browser_baseline"),
            ("b", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        from core.research_bundle_series import bundle_record_to_dict
        d = bundle_record_to_dict(records[0])
        assert "label" in d
        assert "manifest" in d
        assert "artifact_hashes" in d
