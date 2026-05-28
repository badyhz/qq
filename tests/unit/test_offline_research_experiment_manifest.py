"""Tests for offline research experiment manifest.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.offline_research_experiment_manifest import (
    generate_full_manifest,
    save_manifest,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "offline_research_experiment_library"
CATALOG_PATH = FIXTURES / "experiment_catalog.json"


class TestGenerateFullManifest:
    def test_generates_manifest(self):
        manifest = generate_full_manifest(CATALOG_PATH)
        assert manifest["release_hold"] == "HOLD"
        assert manifest["advisory_only"] is True
        assert manifest["human_review_required"] is True
        assert manifest["total_experiments"] >= 20

    def test_all_experiments_valid(self):
        manifest = generate_full_manifest(CATALOG_PATH)
        assert manifest["invalid_experiments"] == 0
        assert manifest["valid_experiments"] >= 20

    def test_manifest_hash_deterministic(self):
        m1 = generate_full_manifest(CATALOG_PATH)
        m2 = generate_full_manifest(CATALOG_PATH)
        assert m1["manifest_hash"] == m2["manifest_hash"]

    def test_experiment_entries_have_hashes(self):
        manifest = generate_full_manifest(CATALOG_PATH)
        for exp in manifest["experiments"]:
            assert "hash" in exp
            assert len(exp["hash"]) == 64

    def test_no_duplicate_hashes(self):
        manifest = generate_full_manifest(CATALOG_PATH)
        hashes = [e["hash"] for e in manifest["experiments"]]
        assert len(hashes) == len(set(hashes))


class TestSaveManifest:
    def test_save_and_reload(self, tmp_path):
        manifest = generate_full_manifest(CATALOG_PATH)
        out = tmp_path / "manifest.json"
        save_manifest(manifest, out)
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded["release_hold"] == "HOLD"
        assert loaded["total_experiments"] >= 20
