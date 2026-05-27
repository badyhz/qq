"""Tests for research artifact index — T4831-T4860."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.research_artifact_index import (
    ArtifactEntry,
    ArtifactIndex,
    artifact_index_to_dict,
    artifact_index_to_json,
    build_artifact_index,
    validate_artifact_index,
)


class TestArtifactIndex:
    def test_builds_from_dir(self, tmp_path):
        (tmp_path / "strategy_registry.json").write_text("{}")
        (tmp_path / "manifest.json").write_text("{}")
        index = build_artifact_index(tmp_path)
        assert len(index.artifacts) == 2

    def test_sha256_computed(self, tmp_path):
        (tmp_path / "strategy_registry.json").write_text('{"test": true}')
        index = build_artifact_index(tmp_path)
        assert index.artifacts[0].sha256 != ""
        assert len(index.artifacts[0].sha256) == 64

    def test_size_bytes(self, tmp_path):
        content = '{"test": "data"}'
        (tmp_path / "manifest.json").write_text(content)
        index = build_artifact_index(tmp_path)
        assert index.artifacts[0].size_bytes == len(content.encode())

    def test_validate_passes(self, tmp_path):
        (tmp_path / "manifest.json").write_text("{}")
        index = build_artifact_index(tmp_path)
        errors = validate_artifact_index(index)
        assert errors == []

    def test_validate_remote_uri(self):
        entry = ArtifactEntry(
            artifact_id="a1", artifact_type="test",
            path="https://example.com/file.json", sha256="abc", size_bytes=10,
        )
        index = ArtifactIndex(artifact_index_id="idx", artifacts=(entry,))
        errors = validate_artifact_index(index)
        assert any("remote" in e for e in errors)

    def test_validate_release_hold(self):
        entry = ArtifactEntry(
            artifact_id="a1", artifact_type="test",
            path="/tmp/test.json", sha256="abc", size_bytes=10, release_hold="READY",
        )
        index = ArtifactIndex(artifact_index_id="idx", artifacts=(entry,))
        errors = validate_artifact_index(index)
        assert any("HOLD" in e for e in errors)


class TestArtifactSerialization:
    def test_to_dict(self, tmp_path):
        (tmp_path / "manifest.json").write_text("{}")
        index = build_artifact_index(tmp_path)
        d = artifact_index_to_dict(index)
        assert d["artifact_index_id"] == "artifact_index_001"
        assert len(d["artifacts"]) == 1

    def test_deterministic_json(self, tmp_path):
        (tmp_path / "manifest.json").write_text("{}")
        index = build_artifact_index(tmp_path)
        j1 = artifact_index_to_json(index)
        j2 = artifact_index_to_json(index)
        assert j1 == j2
