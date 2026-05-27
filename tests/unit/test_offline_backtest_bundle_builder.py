"""Tests for offline backtest bundle builder (Phase 17)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.offline_backtest_bundle_builder import (
    build_backtest_bundle,
    build_manifest,
    compute_sha256,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _make_temp_file(name: str, content: str, tmpdir: Path) -> Path:
    p = tmpdir / name
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# compute_sha256 tests
# ---------------------------------------------------------------------------

class TestComputeSha256:
    def test_deterministic(self, tmp_path):
        f = _make_temp_file("a.txt", "hello world", tmp_path)
        h1 = compute_sha256(f)
        h2 = compute_sha256(f)
        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path):
        f1 = _make_temp_file("a.txt", "hello", tmp_path)
        f2 = _make_temp_file("b.txt", "world", tmp_path)
        assert compute_sha256(f1) != compute_sha256(f2)

    def test_hex_length_64(self, tmp_path):
        f = _make_temp_file("a.txt", "x", tmp_path)
        assert len(compute_sha256(f)) == 64

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            compute_sha256("/nonexistent/file.txt")

    def test_empty_file(self, tmp_path):
        f = _make_temp_file("empty.txt", "", tmp_path)
        h = compute_sha256(f)
        assert len(h) == 64

    def test_binary_file(self, tmp_path):
        p = tmp_path / "bin.dat"
        p.write_bytes(b"\x00\x01\x02\x03")
        h = compute_sha256(p)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# build_manifest tests
# ---------------------------------------------------------------------------

class TestBuildManifest:
    def test_release_hold(self):
        m = build_manifest([])
        assert m["release_hold"] == "HOLD"

    def test_safety_flags(self):
        m = build_manifest([])
        assert m["no_live"] is True
        assert m["no_submit"] is True
        assert m["no_exchange"] is True

    def test_generated_by_field(self):
        m = build_manifest([])
        assert m["generated_by"] == "offline_backtest_bundle_builder"

    def test_empty_artifacts(self):
        m = build_manifest([])
        assert m["artifact_count"] == 0
        assert m["artifacts"] == []

    def test_artifacts_preserved(self):
        arts = [{"name": "a.json", "sha256": "abc", "size_bytes": 100}]
        m = build_manifest(arts)
        assert m["artifact_count"] == 1
        assert m["artifacts"] == arts

    def test_multiple_artifacts(self):
        arts = [
            {"name": "a.json", "sha256": "aaa", "size_bytes": 10},
            {"name": "b.json", "sha256": "bbb", "size_bytes": 20},
            {"name": "c.json", "sha256": "ccc", "size_bytes": 30},
        ]
        m = build_manifest(arts)
        assert m["artifact_count"] == 3
        assert len(m["artifacts"]) == 3


# ---------------------------------------------------------------------------
# build_backtest_bundle tests
# ---------------------------------------------------------------------------

class TestBuildBacktestBundle:
    def test_returns_manifest_dict(self, tmp_path):
        f1 = _make_temp_file("a.json", '{"x":1}', tmp_path)
        result = build_backtest_bundle(tmp_path, {"a.json": str(f1)})
        assert isinstance(result, dict)
        assert result["release_hold"] == "HOLD"

    def test_artifact_count_matches(self, tmp_path):
        f1 = _make_temp_file("a.json", "{}", tmp_path)
        f2 = _make_temp_file("b.json", "{}", tmp_path)
        result = build_backtest_bundle(tmp_path, {"a.json": str(f1), "b.json": str(f2)})
        assert result["artifact_count"] == 2

    def test_sha256_correct(self, tmp_path):
        f = _make_temp_file("a.json", '{"key":"val"}', tmp_path)
        result = build_backtest_bundle(tmp_path, {"a.json": str(f)})
        expected = compute_sha256(f)
        assert result["artifacts"][0]["sha256"] == expected

    def test_size_bytes_correct(self, tmp_path):
        content = "hello world"
        f = _make_temp_file("a.txt", content, tmp_path)
        result = build_backtest_bundle(tmp_path, {"a.txt": str(f)})
        assert result["artifacts"][0]["size_bytes"] == len(content.encode("utf-8"))

    def test_missing_artifact_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            build_backtest_bundle(tmp_path, {"missing.json": "/no/such/file"})

    def test_safety_flags_always_set(self, tmp_path):
        f = _make_temp_file("a.json", "{}", tmp_path)
        result = build_backtest_bundle(tmp_path, {"a.json": str(f)})
        assert result["release_hold"] == "HOLD"
        assert result["no_live"] is True
        assert result["no_submit"] is True
        assert result["no_exchange"] is True

    def test_artifacts_sorted_by_name(self, tmp_path):
        files = {}
        for name in ["z.json", "a.json", "m.json"]:
            f = _make_temp_file(name, "{}", tmp_path)
            files[name] = str(f)
        result = build_backtest_bundle(tmp_path, files)
        names = [a["name"] for a in result["artifacts"]]
        assert names == sorted(names)

    def test_manifest_json_serializable(self, tmp_path):
        f = _make_temp_file("a.json", '{"x":1}', tmp_path)
        result = build_backtest_bundle(tmp_path, {"a.json": str(f)})
        serialized = json.dumps(result)
        deserialized = json.loads(serialized)
        assert deserialized["release_hold"] == "HOLD"
