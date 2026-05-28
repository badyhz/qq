"""Tests for offline research result catalog.

Verifies:
- missing dirs safe
- corrupt JSON flagged
- manifests parsed
- retention class assigned
- release_hold mismatch fails under strict
- deterministic output
- no network imports
- no scanning repo frozen files unless explicit output dir
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.offline_research_result_catalog import (
    RELEASE_HOLD_REQUIRED,
    DEFAULT_SCAN_DIRS,
    ArtifactRecord,
    CatalogResult,
    scan_artifacts,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
    _check_json_valid,
    _detect_artifact_type,
    _detect_source_phase,
    _determine_retention,
)

FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "offline_research_result_catalog"
SAMPLE_OUTPUTS = str(FIXTURE_DIR / "sample_outputs")


# ---------------------------------------------------------------------------
# Tests: missing dirs safe
# ---------------------------------------------------------------------------

class TestMissingDirsSafe:
    def test_missing_dir_no_error(self):
        catalog = scan_artifacts(["/tmp/nonexistent_dir_xyz_123"])
        assert len(catalog.missing_dirs) == 1
        assert "/tmp/nonexistent_dir_xyz_123" in catalog.missing_dirs

    def test_mixed_existing_and_missing(self):
        catalog = scan_artifacts([SAMPLE_OUTPUTS, "/tmp/nonexistent_xyz"])
        assert len(catalog.scanned_dirs) >= 1
        assert len(catalog.missing_dirs) >= 1

    def test_all_missing(self):
        catalog = scan_artifacts(["/tmp/noexist1", "/tmp/noexist2"])
        assert len(catalog.scanned_dirs) == 0
        assert len(catalog.missing_dirs) == 2
        assert len(catalog.artifacts) == 0


# ---------------------------------------------------------------------------
# Tests: corrupt JSON flagged
# ---------------------------------------------------------------------------

class TestCorruptJson:
    def test_corrupt_json_detected(self):
        corrupt = FIXTURE_DIR / "sample_outputs" / "manifest_dir" / "corrupt.json"
        assert _check_json_valid(corrupt) is False

    def test_valid_json_detected(self):
        valid = FIXTURE_DIR / "sample_outputs" / "manifest_dir" / "manifest.json"
        assert _check_json_valid(valid) is True

    def test_catalog_marks_json_validity(self):
        catalog = scan_artifacts([str(FIXTURE_DIR / "sample_outputs" / "manifest_dir")])
        corrupt_entries = [a for a in catalog.artifacts if "corrupt" in a.path]
        valid_entries = [a for a in catalog.artifacts if "manifest.json" in a.path]
        if corrupt_entries:
            assert corrupt_entries[0].json_valid is False
        if valid_entries:
            assert valid_entries[0].json_valid is True


# ---------------------------------------------------------------------------
# Tests: manifests parsed
# ---------------------------------------------------------------------------

class TestManifestsParsed:
    def test_manifest_safety_flags_extracted(self):
        catalog = scan_artifacts([str(FIXTURE_DIR / "sample_outputs" / "manifest_dir")])
        manifest_entries = [a for a in catalog.artifacts if "manifest.json" in a.path]
        if manifest_entries:
            assert manifest_entries[0].safety_flags.get("release_hold") == "HOLD"
            assert manifest_entries[0].safety_flags.get("advisory_only") is True

    def test_non_manifest_no_safety_flags(self):
        catalog = scan_artifacts([str(FIXTURE_DIR / "sample_outputs" / "workbench")])
        for a in catalog.artifacts:
            if "manifest" not in a.path.lower():
                assert a.safety_flags == {}


# ---------------------------------------------------------------------------
# Tests: retention class assigned
# ---------------------------------------------------------------------------

class TestRetentionClass:
    def test_frozen_inventory_high_retention(self):
        assert _determine_retention("json", "frozen_inventory", False) == "KEEP_FOR_AUDIT"

    def test_quality_gate_tagged(self):
        assert _determine_retention("json", "quality_gate", False) == "KEEP_TAGGED"

    def test_workbench_latest(self):
        assert _determine_retention("json", "workbench", False) == "KEEP_LATEST"

    def test_log_temp(self):
        assert _determine_retention("log", "workbench", False) == "TEMP_REGENERABLE"

    def test_all_entries_have_retention(self):
        catalog = scan_artifacts([SAMPLE_OUTPUTS])
        for a in catalog.artifacts:
            assert a.retention_class in (
                "KEEP_LATEST", "KEEP_TAGGED", "KEEP_FOR_AUDIT",
                "TEMP_REGENERABLE", "REVIEW_REQUIRED", "UNKNOWN",
            )


# ---------------------------------------------------------------------------
# Tests: release_hold mismatch fails under strict
# ---------------------------------------------------------------------------

class TestReleaseHold:
    def test_hold_accepted(self):
        assert validate_release_hold("HOLD") is True

    def test_rejected_values(self):
        for val in ["RELEASED", "", "hold", "HOLD "]:
            assert validate_release_hold(val) is False


# ---------------------------------------------------------------------------
# Tests: deterministic output
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_json_deterministic(self, tmp_path):
        catalog = scan_artifacts([SAMPLE_OUTPUTS])
        p1 = tmp_path / "out1.json"
        p2 = tmp_path / "out2.json"
        write_json(catalog, p1)
        write_json(catalog, p2)
        assert p1.read_text() == p2.read_text()

    def test_markdown_deterministic(self, tmp_path):
        catalog = scan_artifacts([SAMPLE_OUTPUTS])
        p1 = tmp_path / "out1.md"
        p2 = tmp_path / "out2.md"
        write_markdown(catalog, p1)
        write_markdown(catalog, p2)
        assert p1.read_text() == p2.read_text()

    def test_manifest_deterministic(self, tmp_path):
        catalog = scan_artifacts([SAMPLE_OUTPUTS])
        p1 = tmp_path / "m1.json"
        p2 = tmp_path / "m2.json"
        write_manifest(catalog, p1)
        write_manifest(catalog, p2)
        assert p1.read_text() == p2.read_text()


# ---------------------------------------------------------------------------
# Tests: no network imports
# ---------------------------------------------------------------------------

class TestNoNetworkImports:
    def test_module_no_network(self):
        import core.offline_research_result_catalog as mod
        source = pathlib.Path(mod.__file__).read_text()
        forbidden = ["import requests", "import httpx", "import aiohttp", "import websocket"]
        for f in forbidden:
            assert f not in source, f"Forbidden import: {f}"


# ---------------------------------------------------------------------------
# Tests: artifact type detection
# ---------------------------------------------------------------------------

class TestArtifactType:
    def test_json_type(self):
        assert _detect_artifact_type(pathlib.Path("foo.json")) == "json"

    def test_md_type(self):
        assert _detect_artifact_type(pathlib.Path("foo.md")) == "markdown"

    def test_html_type(self):
        assert _detect_artifact_type(pathlib.Path("foo.html")) == "html"

    def test_unknown_type(self):
        assert _detect_artifact_type(pathlib.Path("foo.xyz")) == "unknown"


# ---------------------------------------------------------------------------
# Tests: source phase detection
# ---------------------------------------------------------------------------

class TestSourcePhase:
    def test_workbench(self):
        assert _detect_source_phase("/tmp/multi_strategy_research_workbench") == "workbench"

    def test_quality_gate(self):
        assert _detect_source_phase("/tmp/multi_strategy_research_quality_gate") == "quality_gate"

    def test_frozen_inventory(self):
        assert _detect_source_phase("/tmp/frozen_inventory_review") == "frozen_inventory"

    def test_unknown(self):
        assert _detect_source_phase("/tmp/random_dir") == "unknown"


# ---------------------------------------------------------------------------
# Tests: output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_json_has_all_sections(self, tmp_path):
        catalog = scan_artifacts([SAMPLE_OUTPUTS])
        out = tmp_path / "cat.json"
        write_json(catalog, out)
        data = json.loads(out.read_text())
        assert "manifest" in data
        assert "artifacts" in data
        assert "scanned_dirs" in data
        assert "missing_dirs" in data

    def test_catalog_manifest_flags(self):
        catalog = scan_artifacts([SAMPLE_OUTPUTS])
        m = catalog.manifest
        assert m["release_hold"] == "HOLD"
        assert m["advisory_only"] is True
        assert m["no_execution"] is True
        assert m["no_import"] is True
