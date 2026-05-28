"""Tests for research human review CLI scripts.

CLI integration tests. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_human_review"
SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
ROOT = Path(__file__).resolve().parent.parent.parent


def _run(script: str, args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)] + args,
        capture_output=True, text=True, cwd=str(cwd),
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
    )


class TestBuildReviewPacket:
    def test_creates_all_artifacts(self, tmp_path):
        out = tmp_path / "review_output"
        r = _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"

        expected = [
            "review_packet.json",
            "review_checklist.json",
            "review_checklist.md",
            "review_signoff_template.json",
            "review_signoff_template.md",
            "blocker_resolution_ledger.json",
            "blocker_resolution_ledger.md",
            "review_audit_trail.json",
            "review_audit_trail.md",
            "human_review_report.md",
            "human_review_report.html",
            "review_manifest.json",
        ]
        for name in expected:
            assert (out / name).exists(), f"missing: {name}"

    def test_missing_quality_dir_fails(self, tmp_path):
        out = tmp_path / "review_output"
        r = _run("build_research_human_review_packet.py", [
            "--quality-dir", str(tmp_path / "nonexistent"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        assert r.returncode != 0

    def test_invalid_release_hold_fails(self, tmp_path):
        out = tmp_path / "review_output"
        r = _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "NOT_HOLD",
        ])
        assert r.returncode != 0

    def test_packet_safety_flags(self, tmp_path):
        out = tmp_path / "review_output"
        _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        packet = json.loads((out / "review_packet.json").read_text())
        assert packet["release_hold"] == "HOLD"
        assert packet["advisory_only"] is True
        assert packet["no_network"] is True


class TestValidateReviewPacket:
    def test_valid_packet_passes(self, tmp_path):
        out = tmp_path / "review_output"
        _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        r = _run("validate_research_human_review_packet.py", [
            "--review-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"
        assert "PASS" in r.stdout

    def test_invalid_release_hold_fails(self, tmp_path):
        r = _run("validate_research_human_review_packet.py", [
            "--review-dir", str(tmp_path),
            "--strict",
            "--release-hold", "NOT_HOLD",
        ])
        assert r.returncode != 0

    def test_missing_dir_fails(self, tmp_path):
        r = _run("validate_research_human_review_packet.py", [
            "--review-dir", str(tmp_path / "nonexistent"),
            "--strict",
            "--release-hold", "HOLD",
        ])
        assert r.returncode != 0

    def test_completed_signoff_valid(self, tmp_path):
        """Validate valid completed signoff passes."""
        out = tmp_path / "review_output"
        _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        # Copy valid signoff
        import shutil
        src = FIXTURES / "signoff_valid_request_more_research" / "review_signoff_completed.json"
        shutil.copy2(src, out / "review_signoff_completed.json")
        r = _run("validate_research_human_review_packet.py", [
            "--review-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"

    def test_completed_signoff_approve_live_fails(self, tmp_path):
        """Validate APPROVE_LIVE signoff fails."""
        out = tmp_path / "review_output"
        _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        import shutil
        src = FIXTURES / "signoff_invalid_approve_live" / "review_signoff_completed.json"
        shutil.copy2(src, out / "review_signoff_completed.json")
        r = _run("validate_research_human_review_packet.py", [
            "--review-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        assert r.returncode != 0


class TestRenderReviewReport:
    def test_render_deterministic(self, tmp_path):
        build_out = tmp_path / "review_output"
        _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(build_out),
            "--strict",
            "--release-hold", "HOLD",
        ])

        render1 = tmp_path / "rendered1"
        render2 = tmp_path / "rendered2"
        _run("render_research_human_review_report.py", [
            "--review-dir", str(build_out),
            "--output-dir", str(render1),
        ])
        _run("render_research_human_review_report.py", [
            "--review-dir", str(build_out),
            "--output-dir", str(render2),
        ])

        md1 = (render1 / "human_review_report.md").read_text()
        md2 = (render2 / "human_review_report.md").read_text()
        assert md1 == md2

    def test_render_creates_files(self, tmp_path):
        build_out = tmp_path / "review_output"
        _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(build_out),
            "--strict",
            "--release-hold", "HOLD",
        ])

        render_out = tmp_path / "rendered"
        r = _run("render_research_human_review_report.py", [
            "--review-dir", str(build_out),
            "--output-dir", str(render_out),
        ])
        assert r.returncode == 0
        assert (render_out / "human_review_report.md").exists()
        assert (render_out / "human_review_report.html").exists()


class TestForbiddenStrings:
    """Prove no generated artifact allows live/testnet/runtime approval."""

    def test_packet_forbidden_decisions(self, tmp_path):
        out = tmp_path / "review_output"
        _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        packet = json.loads((out / "review_packet.json").read_text())
        forbidden = {"APPROVE_LIVE", "APPROVE_TESTNET_SUBMIT", "APPROVE_RUNTIME", "AUTO_PROMOTE"}
        for fd in forbidden:
            assert fd not in packet["allowed_decisions"], f"{fd} in allowed_decisions"
            assert fd in packet["forbidden_decisions"], f"{fd} not in forbidden_decisions"

    def test_manifest_safety(self, tmp_path):
        out = tmp_path / "review_output"
        _run("build_research_human_review_packet.py", [
            "--quality-dir", str(FIXTURES / "source_quality_gate"),
            "--artifact-browser-dir", str(FIXTURES / "source_artifact_browser"),
            "--comparison-dir", str(FIXTURES / "source_comparison"),
            "--output-dir", str(out),
            "--strict",
            "--release-hold", "HOLD",
        ])
        manifest = json.loads((out / "review_manifest.json").read_text())
        assert manifest["release_hold"] == "HOLD"
        assert manifest["advisory_only"] is True
        assert manifest["no_live"] is True
        assert manifest["no_network"] is True
