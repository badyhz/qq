"""T1868 - Frozen Backlog Manifest Tests.

Tests manifest creation, immutability, hash computation, rendering.
At least 10 tests. No network. tmp_path for file I/O.
"""
from __future__ import annotations

import json
import os
import pathlib

import pytest

from core.frozen_backlog_artifact_entry import ArtifactEntry
from core.frozen_backlog_manifest import FrozenBacklogManifest
from core.frozen_backlog_manifest_builder import build_manifest
from core.frozen_backlog_manifest_renderer import (
    render_manifest_json,
    render_manifest_md,
)


# --- ArtifactEntry ---


class TestArtifactEntry:
    def test_frozen(self) -> None:
        entry = ArtifactEntry(filename="a.txt", size_bytes=10, sha256_hash="abc")
        with pytest.raises(AttributeError):
            entry.filename = "b.txt"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        entry = ArtifactEntry(filename="a.txt", size_bytes=10, sha256_hash="abc")
        d = entry.to_dict()
        assert d == {"filename": "a.txt", "size_bytes": 10, "sha256_hash": "abc"}

    def test_equality(self) -> None:
        a = ArtifactEntry(filename="a.txt", size_bytes=10, sha256_hash="abc")
        b = ArtifactEntry(filename="a.txt", size_bytes=10, sha256_hash="abc")
        assert a == b


# --- FrozenBacklogManifest ---


class TestFrozenBacklogManifest:
    def _make_manifest(self, **overrides: object) -> FrozenBacklogManifest:
        kwargs = {
            "manifest_id": "test-manifest",
            "artifacts": (
                ArtifactEntry("a.txt", 10, "hash_a"),
            ),
            "generated_by": "test",
            "release_hold": "HOLD",
            "no_live": True,
            "no_submit": True,
            "no_exchange": True,
            "no_runtime_integration": True,
            "no_planner_integration": True,
        }
        kwargs.update(overrides)
        return FrozenBacklogManifest(**kwargs)  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        m = self._make_manifest()
        with pytest.raises(AttributeError):
            m.release_hold = "RELEASED"  # type: ignore[misc]

    def test_hold_required(self) -> None:
        with pytest.raises(ValueError, match="release_hold"):
            self._make_manifest(release_hold="RELEASED")

    def test_no_live_required(self) -> None:
        with pytest.raises(ValueError, match="no_live"):
            self._make_manifest(no_live=False)

    def test_no_submit_required(self) -> None:
        with pytest.raises(ValueError, match="no_submit"):
            self._make_manifest(no_submit=False)

    def test_no_exchange_required(self) -> None:
        with pytest.raises(ValueError, match="no_exchange"):
            self._make_manifest(no_exchange=False)

    def test_to_dict(self) -> None:
        m = self._make_manifest()
        d = m.to_dict()
        assert d["release_hold"] == "HOLD"
        assert d["no_live"] is True
        assert len(d["artifacts"]) == 1

    def test_to_dict_artifact_structure(self) -> None:
        m = self._make_manifest()
        d = m.to_dict()
        artifact = d["artifacts"][0]
        assert artifact["filename"] == "a.txt"
        assert artifact["size_bytes"] == 10
        assert artifact["sha256_hash"] == "hash_a"


# --- build_manifest ---


class TestBuildManifest:
    def test_creates_manifest(self, tmp_path: object) -> None:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "a.txt"
        f1.write_text("hello", encoding="utf-8")
        manifest = build_manifest((str(f1),), generated_by="test")
        assert isinstance(manifest, FrozenBacklogManifest)
        assert manifest.release_hold == "HOLD"

    def test_artifact_count(self, tmp_path: object) -> None:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "a.txt"
        f2 = base / "b.txt"
        f1.write_text("hello", encoding="utf-8")
        f2.write_text("world", encoding="utf-8")
        manifest = build_manifest((str(f1), str(f2)), generated_by="test")
        assert len(manifest.artifacts) == 2

    def test_sha256_correct(self, tmp_path: object) -> None:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "a.txt"
        f1.write_text("hello", encoding="utf-8")
        manifest = build_manifest((str(f1),), generated_by="test")
        entry = manifest.artifacts[0]
        # sha256 of "hello"
        assert entry.sha256_hash == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_size_correct(self, tmp_path: object) -> None:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "a.txt"
        f1.write_text("hello", encoding="utf-8")
        manifest = build_manifest((str(f1),), generated_by="test")
        entry = manifest.artifacts[0]
        assert entry.size_bytes == 5

    def test_filename_correct(self, tmp_path: object) -> None:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "report.md"
        f1.write_text("# Report", encoding="utf-8")
        manifest = build_manifest((str(f1),), generated_by="test")
        assert manifest.artifacts[0].filename == "report.md"

    def test_generated_by(self, tmp_path: object) -> None:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "a.txt"
        f1.write_text("x", encoding="utf-8")
        manifest = build_manifest((str(f1),), generated_by="custom_platform")
        assert manifest.generated_by == "custom_platform"

    def test_safety_flags_enforced(self, tmp_path: object) -> None:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "a.txt"
        f1.write_text("x", encoding="utf-8")
        manifest = build_manifest((str(f1),), generated_by="test")
        assert manifest.no_live is True
        assert manifest.no_submit is True
        assert manifest.no_exchange is True
        assert manifest.no_runtime_integration is True
        assert manifest.no_planner_integration is True


# --- render_manifest_json ---


class TestRenderManifestJson:
    def _manifest(self, tmp_path: object) -> FrozenBacklogManifest:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "a.txt"
        f1.write_text("hello", encoding="utf-8")
        return build_manifest((str(f1),), generated_by="test")

    def test_valid_json(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        raw = render_manifest_json(m)
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_has_artifacts_key(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        raw = render_manifest_json(m)
        parsed = json.loads(raw)
        assert "artifacts" in parsed

    def test_release_hold_in_json(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        raw = render_manifest_json(m)
        parsed = json.loads(raw)
        assert parsed["release_hold"] == "HOLD"

    def test_deterministic(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        a = render_manifest_json(m)
        b = render_manifest_json(m)
        assert a == b

    def test_key_ordering(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        raw = render_manifest_json(m)
        parsed = json.loads(raw)
        keys = list(parsed.keys())
        assert keys == sorted(keys)


# --- render_manifest_md ---


class TestRenderManifestMd:
    def _manifest(self, tmp_path: object) -> FrozenBacklogManifest:
        base = pathlib.Path(str(tmp_path))
        f1 = base / "a.txt"
        f1.write_text("hello", encoding="utf-8")
        return build_manifest((str(f1),), generated_by="test")

    def test_contains_title(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        md = render_manifest_md(m)
        assert "Frozen Backlog Manifest" in md

    def test_contains_release_hold(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        md = render_manifest_md(m)
        assert "HOLD" in md

    def test_contains_artifacts_table(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        md = render_manifest_md(m)
        assert "| Filename" in md
        assert "a.txt" in md

    def test_contains_safety_flags(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        md = render_manifest_md(m)
        assert "No Live" in md
        assert "No Submit" in md

    def test_deterministic(self, tmp_path: object) -> None:
        m = self._manifest(tmp_path)
        a = render_manifest_md(m)
        b = render_manifest_md(m)
        assert a == b
