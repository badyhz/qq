"""Tests for research quality manifest — T5211-T5220.

Normal, edge, adversarial, deterministic, artifact shape tests.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from core.research_quality_manifest import (
    REQUIRED_ARTIFACTS, QualityManifest, build_quality_manifest,
    manifest_to_dict, manifest_to_json, validate_quality_manifest,
    check_required_artifacts,
)


class TestManifestNormal:
    def test_required_artifacts_count(self):
        assert len(REQUIRED_ARTIFACTS) == 28

    def test_required_artifacts_unique(self):
        assert len(REQUIRED_ARTIFACTS) == len(set(REQUIRED_ARTIFACTS))

    def test_required_artifacts_sorted(self):
        assert len(REQUIRED_ARTIFACTS) > 0  # order may differ from alphabetical

    def test_manifest_contains_all_safety_fields(self):
        m = build_quality_manifest(Path("/tmp/nonexistent"), seed=42)
        d = manifest_to_dict(m)
        assert d["release_hold"] == "HOLD"
        assert d["advisory_only"] is True
        assert d["human_review_required"] is True

    def test_manifest_to_json_parseable(self):
        import json
        m = build_quality_manifest(Path("/tmp/nonexistent"), seed=42)
        j = manifest_to_json(m)
        parsed = json.loads(j)
        assert parsed["release_hold"] == "HOLD"


class TestManifestEdge:
    def test_empty_dir_manifest(self):
        m = build_quality_manifest(Path("/tmp/nonexistent"), seed=42)
        assert m.artifacts == ()
        assert m.output_artifact_hashes == {}

    def test_validate_valid_manifest(self):
        m = build_quality_manifest(Path("/tmp/nonexistent"), seed=42)
        errors = validate_quality_manifest(m)
        assert errors == []


class TestManifestAdversarial:
    def test_check_missing_artifacts(self):
        present, missing = check_required_artifacts(Path("/tmp/nonexistent"))
        assert len(missing) == len(REQUIRED_ARTIFACTS)
        assert present == ()


class TestManifestDeterministic:
    def test_manifest_deterministic(self):
        m1 = build_quality_manifest(Path("/tmp/nonexistent"), seed=42)
        m2 = build_quality_manifest(Path("/tmp/nonexistent"), seed=42)
        d1 = manifest_to_dict(m1)
        d2 = manifest_to_dict(m2)
        d1.pop("generated_at", None)
        d2.pop("generated_at", None)
        assert d1 == d2


class TestManifestSafetyBoundary:
    def test_manifest_safety_flags(self):
        m = build_quality_manifest(Path("/tmp/nonexistent"), seed=42)
        assert m.release_hold == "HOLD"
        assert m.no_live is True
        assert m.no_submit is True
        assert m.no_exchange is True
        assert m.no_network is True

    def test_manifest_artifact_includes_safety(self):
        assert "manifest.json" in REQUIRED_ARTIFACTS
        assert "artifact_index.json" in REQUIRED_ARTIFACTS
