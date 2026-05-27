"""Tests for research reproducibility manifest — T8321-T8360.

Manifest required fields tests.
"""
from __future__ import annotations

import pytest
from core.research_reproducibility_manifest import build_reproducibility_manifest


class TestReproducibilityManifestNormal:
    def test_build_manifest(self):
        m = build_reproducibility_manifest(42, {"a.json": "hash1"}, {"b.json": "hash2"})
        assert m["release_hold"] == "HOLD"
        assert m["deterministic_seed"] == 42

    def test_has_all_safety_flags(self):
        m = build_reproducibility_manifest(42, {}, {})
        assert m["no_live"] is True
        assert m["no_submit"] is True
        assert m["no_exchange"] is True
        assert m["no_network"] is True


class TestReproducibilityManifestSafetyBoundary:
    def test_manifest_safety(self):
        m = build_reproducibility_manifest(42, {}, {})
        assert m["release_hold"] == "HOLD"
        assert m["advisory_only"] is True
        assert m["human_review_required"] is True
