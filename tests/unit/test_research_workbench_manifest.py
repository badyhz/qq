"""Tests for research workbench manifest builder — T4861-T4890."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.research_workbench_manifest import (
    WorkbenchManifest,
    build_manifest,
    manifest_to_dict,
    manifest_to_json,
    validate_manifest,
)


class TestManifestBuilder:
    def test_builds_manifest(self, tmp_path):
        (tmp_path / "strategy_registry.json").write_text("{}")
        (tmp_path / "manifest.json").write_text("{}")
        m = build_manifest(tmp_path)
        assert m.release_hold == "HOLD"
        assert m.no_live is True
        assert m.no_submit is True

    def test_missing_artifacts(self, tmp_path):
        m = build_manifest(tmp_path, required_artifacts=["strategy_registry.json", "manifest.json"])
        assert any("MISSING" in w for w in m.warnings)
        assert m.validation_status == "WARN"

    def test_sha256_computed(self, tmp_path):
        (tmp_path / "strategy_registry.json").write_text('{"test": true}')
        m = build_manifest(tmp_path, required_artifacts=["strategy_registry.json", "manifest.json"])
        assert "strategy_registry.json" in m.sha256

    def test_validation_passes(self, tmp_path):
        m = build_manifest(tmp_path)
        errors = validate_manifest(m)
        assert errors == []


class TestManifestValidation:
    def test_wrong_release_hold(self):
        m = WorkbenchManifest(
            manifest_id="test", generated_by="test",
            release_hold="READY", no_live=True, no_submit=True,
            no_exchange=True, no_runtime_integration=True,
            no_planner_integration=True, no_network=True,
            artifacts=(), sha256={}, artifact_sizes={},
            warnings=(), validation_status="PASS",
        )
        errors = validate_manifest(m)
        assert any("HOLD" in e for e in errors)

    def test_no_live_false(self):
        m = WorkbenchManifest(
            manifest_id="test", generated_by="test",
            release_hold="HOLD", no_live=False, no_submit=True,
            no_exchange=True, no_runtime_integration=True,
            no_planner_integration=True, no_network=True,
            artifacts=(), sha256={}, artifact_sizes={},
            warnings=(), validation_status="PASS",
        )
        errors = validate_manifest(m)
        assert any("no_live" in e for e in errors)


class TestManifestSerialization:
    def test_to_dict(self, tmp_path):
        m = build_manifest(tmp_path)
        d = manifest_to_dict(m)
        assert d["release_hold"] == "HOLD"
        assert isinstance(d["sha256"], dict)

    def test_deterministic_json(self, tmp_path):
        (tmp_path / "strategy_registry.json").write_text("{}")
        m = build_manifest(tmp_path, required_artifacts=["strategy_registry.json", "manifest.json"])
        j1 = manifest_to_json(m)
        j2 = manifest_to_json(m)
        assert j1 == j2
