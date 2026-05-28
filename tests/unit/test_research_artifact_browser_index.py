"""Tests for research artifact browser indexer — T9361-T9800.

Required coverage, missing artifacts, corrupted JSON, deterministic output.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.research_artifact_browser import (
    build_artifact_browser_index,
    artifact_browser_index_to_dict,
)
from core.research_artifact_schema import BROWSER_REQUIRED_ARTIFACTS


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_artifact_browser"


class TestBrowserIndexRequiredCoverage:
    def test_all_required_present_pass(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        assert idx.required_present == len(BROWSER_REQUIRED_ARTIFACTS)
        assert idx.required_missing == 0

    def test_index_covers_all_required_names(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        indexed_names = {e.name for e in idx.entries if e.required}
        assert indexed_names == set(BROWSER_REQUIRED_ARTIFACTS)

    def test_optional_artifacts_detected(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        optional = [e for e in idx.entries if not e.required]
        assert len(optional) >= 2


class TestBrowserIndexMissingRequired:
    def test_missing_required_status_fail(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_missing_required")
        assert idx.status == "FAIL"

    def test_missing_required_count(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_missing_required")
        assert idx.required_missing > 0
        assert idx.required_present < len(BROWSER_REQUIRED_ARTIFACTS)


class TestBrowserIndexCorruptedJson:
    def test_corrupted_json_flagged(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_corrupted_json")
        corrupted = [e for e in idx.entries if e.name == "quality_gate_summary.json"]
        assert len(corrupted) == 1
        assert corrupted[0].json_parse_ok is False
        assert corrupted[0].exists is True

    def test_valid_json_still_ok(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_corrupted_json")
        manifest = [e for e in idx.entries if e.name == "manifest.json"]
        assert len(manifest) == 1
        assert manifest[0].json_parse_ok is True


class TestBrowserIndexDeterministic:
    def test_output_deterministic(self):
        d = FIXTURES / "quality_bundle_pass"
        r1 = json.dumps(artifact_browser_index_to_dict(
            build_artifact_browser_index(d)), sort_keys=True)
        r2 = json.dumps(artifact_browser_index_to_dict(
            build_artifact_browser_index(d)), sort_keys=True)
        assert r1 == r2

    def test_entries_sorted(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        names = [e.name for e in idx.entries]
        assert names == sorted(names)


class TestBrowserIndexShape:
    def test_entry_has_required_fields(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        for e in idx.entries:
            assert hasattr(e, "name")
            assert hasattr(e, "required")
            assert hasattr(e, "exists")
            assert hasattr(e, "sha256")
            assert hasattr(e, "size_bytes")
            assert hasattr(e, "json_parse_ok")
            assert hasattr(e, "top_level_keys")

    def test_dict_serialization(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        d = artifact_browser_index_to_dict(idx)
        assert "entries" in d
        assert "required_present" in d
        assert "status" in d
        assert d["release_hold"] == "HOLD"


class TestBrowserIndexAdversarial:
    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            idx = build_artifact_browser_index(Path(d))
            assert idx.status == "FAIL"
            assert idx.required_missing == len(BROWSER_REQUIRED_ARTIFACTS)
            assert idx.required_present == 0

    def test_nonexistent_directory(self):
        with tempfile.TemporaryDirectory() as d:
            idx = build_artifact_browser_index(Path(d) / "nonexistent")
            assert idx.status == "FAIL"
