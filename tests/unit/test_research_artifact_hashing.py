"""Tests for research artifact hashing — T8281-T8320.

Hash stable, changed artifact, missing artifact tests.
"""
from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path
from core.research_artifact_hashing import (
    hash_file, hash_artifact_content, compute_artifact_hashes,
    compare_hashes, TIMESTAMP_ALLOWLIST,
)


class TestArtifactHashingNormal:
    def test_hash_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            f.flush()
            h = hash_file(Path(f.name))
            assert len(h) == 64

    def test_hash_artifact_content(self):
        h = hash_artifact_content({"key": "value"})
        assert len(h) == 64

    def test_compute_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.json").write_text(json.dumps({"v": 1}))
            hashes = compute_artifact_hashes(Path(d), ("a.json",))
            assert "a.json" in hashes


class TestArtifactHashingEdge:
    def test_missing_file(self):
        h = hash_file(Path("/tmp/nonexistent_file"))
        assert h == ""


class TestArtifactHashingDeterministic:
    def test_stable_hash(self):
        data = {"b": 2, "a": 1}
        h1 = hash_artifact_content(data)
        h2 = hash_artifact_content(data)
        assert h1 == h2

    def test_timestamp_excluded(self):
        d1 = {"key": "value", "generated_at": "2024-01-01"}
        d2 = {"key": "value", "generated_at": "2024-12-31"}
        h1 = hash_artifact_content(d1, exclude_timestamps=True)
        h2 = hash_artifact_content(d2, exclude_timestamps=True)
        assert h1 == h2


class TestArtifactHashingSafetyBoundary:
    def test_timestamp_allowlist(self):
        assert "generated_at" in TIMESTAMP_ALLOWLIST
