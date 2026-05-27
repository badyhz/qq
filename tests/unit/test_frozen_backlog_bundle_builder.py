"""T1858 - Frozen Backlog Bundle Builder Tests.

Tests the bundle builder creates all expected files, manifest has correct
structure, hashes match. Uses tmp_path for I/O.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "build_frozen_backlog_review_bundle.py")

EXPECTED_FILES = (
    "report.md",
    "report.json",
    "validation.json",
    "validation.md",
    "snapshot.json",
    "dashboard.html",
    "board_packet.md",
    "manifest.json",
)


@pytest.fixture(scope="module")
def bundle_dir(tmp_path_factory: object) -> str:
    """Run bundle builder once, return output directory path."""
    d = str(tmp_path_factory.mktemp("bundle"))  # type: ignore[union-attr]
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    result = subprocess.run(
        [sys.executable, SCRIPT, "--output-dir", d],
        capture_output=True, text=True, cwd=PROJECT_ROOT, env=env,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return d


class TestBundleFiles:
    def test_all_expected_files_exist(self, bundle_dir: str) -> None:
        for filename in EXPECTED_FILES:
            path = os.path.join(bundle_dir, filename)
            assert os.path.exists(path), f"Missing: {filename}"

    def test_report_md_not_empty(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "report.md")
        assert os.path.getsize(path) > 0

    def test_report_json_valid(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "report.json")
        with open(path, "r") as f:
            data = json.load(f)
        assert "summary" in data
        assert "records" in data

    def test_validation_json_valid(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "validation.json")
        with open(path, "r") as f:
            data = json.load(f)
        assert "is_valid" in data
        assert "checks_passed" in data
        assert "checks_failed" in data

    def test_snapshot_json_valid(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "snapshot.json")
        with open(path, "r") as f:
            data = json.load(f)
        assert data["release_hold"] == "HOLD"
        assert data["no_live"] is True
        assert data["total_count"] == 22

    def test_dashboard_html_is_html(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "dashboard.html")
        with open(path, "r") as f:
            content = f.read()
        assert content.startswith("<!DOCTYPE html>")

    def test_board_packet_md_not_empty(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "board_packet.md")
        assert os.path.getsize(path) > 0
        with open(path, "r") as f:
            content = f.read()
        assert "Board Packet" in content

    def test_report_json_has_22_records(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "report.json")
        with open(path, "r") as f:
            data = json.load(f)
        assert len(data["records"]) == 22


class TestManifest:
    def test_manifest_valid_json(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "manifest.json")
        with open(path, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_manifest_has_generated_by(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "manifest.json")
        with open(path, "r") as f:
            data = json.load(f)
        assert data["generated_by"] == "frozen_backlog_review_platform"

    def test_manifest_has_release_hold(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "manifest.json")
        with open(path, "r") as f:
            data = json.load(f)
        assert data["release_hold"] == "HOLD"

    def test_manifest_has_safety_flags(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "manifest.json")
        with open(path, "r") as f:
            data = json.load(f)
        assert data["no_live"] is True
        assert data["no_submit"] is True
        assert data["no_exchange"] is True

    def test_manifest_artifacts_count(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "manifest.json")
        with open(path, "r") as f:
            data = json.load(f)
        # 7 artifacts (all except manifest.json itself)
        assert len(data["artifacts"]) == 7

    def test_manifest_artifact_structure(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "manifest.json")
        with open(path, "r") as f:
            data = json.load(f)
        for artifact in data["artifacts"]:
            assert "filename" in artifact
            assert "size_bytes" in artifact
            assert "sha256_hash" in artifact

    def test_manifest_hashes_match_actual(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "manifest.json")
        with open(path, "r") as f:
            data = json.load(f)
        for artifact in data["artifacts"]:
            filename = artifact["filename"]
            expected_hash = artifact["sha256_hash"]
            actual_path = os.path.join(bundle_dir, filename)
            h = hashlib.sha256()
            with open(actual_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            assert h.hexdigest() == expected_hash, (
                f"Hash mismatch for {filename}"
            )

    def test_manifest_file_sizes_match(self, bundle_dir: str) -> None:
        path = os.path.join(bundle_dir, "manifest.json")
        with open(path, "r") as f:
            data = json.load(f)
        for artifact in data["artifacts"]:
            filename = artifact["filename"]
            expected_size = artifact["size_bytes"]
            actual_path = os.path.join(bundle_dir, filename)
            actual_size = os.path.getsize(actual_path)
            assert actual_size == expected_size, (
                f"Size mismatch for {filename}"
            )
