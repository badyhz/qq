"""Tests for research quality bundle — T5251-T5260.

Atomic write, overwrite, missing output-dir, skeleton tests.
"""
from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path
from core.research_quality_bundle import write_artifact, write_bundle_skeleton


class TestBundleNormal:
    def test_write_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_artifact(Path(d), "test.json", {"key": "value"})
            assert p.exists()
            data = json.loads(p.read_text())
            assert data["key"] == "value"

    def test_write_skeleton(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_bundle_skeleton(Path(d), seed=42)
            assert p.exists()
            data = json.loads(p.read_text())
            assert data["release_hold"] == "HOLD"
            assert data["advisory_only"] is True

    def test_skeleton_creates_index(self):
        with tempfile.TemporaryDirectory() as d:
            write_bundle_skeleton(Path(d), seed=42)
            assert (Path(d) / "artifact_index.json").exists()


class TestBundleEdge:
    def test_write_creates_dir(self):
        with tempfile.TemporaryDirectory() as d:
            subdir = Path(d) / "nested" / "dir"
            p = write_artifact(subdir, "test.json", {"x": 1})
            assert p.exists()

    def test_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            write_artifact(Path(d), "test.json", {"v": 1})
            write_artifact(Path(d), "test.json", {"v": 2})
            data = json.loads((Path(d) / "test.json").read_text())
            assert data["v"] == 2


class TestBundleAdversarial:
    def test_empty_data(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_artifact(Path(d), "empty.json", {})
            assert p.exists()


class TestBundleDeterministic:
    def test_skeleton_deterministic(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            write_bundle_skeleton(Path(d1), seed=42)
            write_bundle_skeleton(Path(d2), seed=42)
            m1 = json.loads((Path(d1) / "manifest.json").read_text())
            m2 = json.loads((Path(d2) / "manifest.json").read_text())
            # Remove generated_at for comparison
            m1.pop("generated_at", None)
            m2.pop("generated_at", None)
            assert m1 == m2


class TestBundleSafetyBoundary:
    def test_skeleton_safety_flags(self):
        with tempfile.TemporaryDirectory() as d:
            write_bundle_skeleton(Path(d), seed=42)
            m = json.loads((Path(d) / "manifest.json").read_text())
            assert m["release_hold"] == "HOLD"
            assert m["no_live"] is True
            assert m["no_submit"] is True
            assert m["no_exchange"] is True
            assert m["no_network"] is True
