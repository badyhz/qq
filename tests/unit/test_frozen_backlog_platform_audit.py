"""T1871-T1880 - Tests for frozen backlog platform audit runner."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.run_frozen_backlog_platform_audit import (
    EXPECTED_FILES,
    run_platform_audit,
)


@pytest.fixture()
def tmp_out(tmp_path):
    return str(tmp_path / "audit_output")


class TestPlatformAudit:
    def test_platform_audit_full_mode_creates_all_files(self, tmp_out):
        run_platform_audit(tmp_out, mode="full")
        for fname in EXPECTED_FILES:
            fpath = os.path.join(tmp_out, fname)
            assert os.path.exists(fpath), f"Missing: {fname}"

    def test_platform_audit_pass_exit_code(self, tmp_out):
        exit_code = run_platform_audit(tmp_out, mode="full")
        assert exit_code == 0

    def test_platform_audit_manifest_hashes_valid(self, tmp_out):
        run_platform_audit(tmp_out, mode="full")
        manifest_path = os.path.join(tmp_out, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for entry in manifest["artifacts"]:
            fname = entry["filename"]
            expected = entry["sha256_hash"]
            fpath = os.path.join(tmp_out, fname)
            assert os.path.exists(fpath), f"Artifact missing: {fname}"

            import hashlib
            h = hashlib.sha256()
            with open(fpath, "rb") as af:
                for chunk in iter(lambda: af.read(8192), b""):
                    h.update(chunk)
            actual = h.hexdigest()
            assert actual == expected, f"Hash mismatch for {fname}"

    def test_platform_audit_dashboard_html_exists(self, tmp_out):
        run_platform_audit(tmp_out, mode="full")
        html_path = os.path.join(tmp_out, "dashboard.html")
        assert os.path.exists(html_path)
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "Frozen Backlog Review Dashboard" in content

    def test_platform_audit_board_packet_exists(self, tmp_out):
        run_platform_audit(tmp_out, mode="full")
        bp_path = os.path.join(tmp_out, "board_packet.md")
        assert os.path.exists(bp_path)
        with open(bp_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Board Packet" in content
        assert "HOLD" in content

    def test_platform_audit_summary_mode(self, tmp_out):
        exit_code = run_platform_audit(tmp_out, mode="summary")
        assert exit_code == 0
        for fname in EXPECTED_FILES:
            fpath = os.path.join(tmp_out, fname)
            assert os.path.exists(fpath), f"Missing in summary mode: {fname}"
