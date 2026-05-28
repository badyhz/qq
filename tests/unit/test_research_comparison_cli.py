"""Tests for research comparison CLI scripts.

CLI integration tests. Offline only. No network.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_comparison_analytics"
SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
ROOT = Path(__file__).resolve().parent.parent.parent

EXPECTED_ARTIFACTS = (
    "bundle_series_index.json",
    "extracted_metrics.json",
    "pairwise_comparison.json",
    "trend_report.json",
    "regression_report.json",
    "comparison_scorecard.json",
    "research_comparison_report.md",
    "research_comparison_report.html",
    "research_comparison_manifest.json",
)


class TestBuildComparisonCLI:
    """Test build_research_comparison_analytics.py CLI."""

    def test_cli_creates_all_artifacts(self, tmp_path):
        """Test CLI creates all expected artifacts."""
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "build_research_comparison_analytics.py"),
                "--bundle", f"baseline={FIXTURES / 'artifact_browser_baseline'}",
                "--bundle", f"candidate={FIXTURES / 'artifact_browser_candidate_improved'}",
                "--output-dir", str(tmp_path / "output"),
                "--strict",
                "--release-hold", "HOLD",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        for name in EXPECTED_ARTIFACTS:
            assert (tmp_path / "output" / name).exists(), f"Missing: {name}"

    def test_cli_rejects_one_bundle(self, tmp_path):
        """Test CLI exits non-zero with 1 bundle."""
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "build_research_comparison_analytics.py"),
                "--bundle", f"only={FIXTURES / 'artifact_browser_baseline'}",
                "--output-dir", str(tmp_path / "output"),
                "--strict",
                "--release-hold", "HOLD",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        )
        assert result.returncode != 0

    def test_cli_rejects_invalid_safety(self, tmp_path):
        """Test CLI exits non-zero on invalid safety flags."""
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "build_research_comparison_analytics.py"),
                "--bundle", f"baseline={FIXTURES / 'artifact_browser_baseline'}",
                "--bundle", f"invalid={FIXTURES / 'artifact_browser_invalid_safety'}",
                "--output-dir", str(tmp_path / "output"),
                "--strict",
                "--release-hold", "HOLD",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        )
        assert result.returncode != 0

    def test_cli_manifest_contains_safety_flags(self, tmp_path):
        """Test CLI manifest has correct safety flags."""
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "build_research_comparison_analytics.py"),
                "--bundle", f"baseline={FIXTURES / 'artifact_browser_baseline'}",
                "--bundle", f"candidate={FIXTURES / 'artifact_browser_candidate_improved'}",
                "--output-dir", str(tmp_path / "output"),
                "--strict",
                "--release-hold", "HOLD",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        )
        manifest_path = tmp_path / "output" / "research_comparison_manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["release_hold"] == "HOLD"
        assert manifest["advisory_only"] is True
        assert manifest["human_review_required"] is True
        assert manifest["no_network"] is True
        assert manifest["no_live"] is True
        assert manifest["no_submit"] is True
        assert manifest["no_exchange"] is True
        assert manifest["no_runtime_integration"] is True
        assert manifest["no_planner_integration"] is True


class TestCompareQualitySeriesCLI:
    """Test compare_research_quality_series.py CLI."""

    def test_cli_creates_all_artifacts(self, tmp_path):
        """Test CLI creates all expected artifacts."""
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "compare_research_quality_series.py"),
                "--bundle", f"baseline={FIXTURES / 'quality_gate_baseline'}",
                "--bundle", f"candidate={FIXTURES / 'quality_gate_candidate_changed'}",
                "--output-dir", str(tmp_path / "output"),
                "--strict",
                "--release-hold", "HOLD",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        )
        assert result.returncode == 0 or result.returncode == 1, f"stderr: {result.stderr}"
        for name in EXPECTED_ARTIFACTS:
            assert (tmp_path / "output" / name).exists(), f"Missing: {name}"


class TestRenderReportCLI:
    """Test render_research_comparison_report.py CLI."""

    def test_render_deterministic(self, tmp_path):
        """Test rendered report is deterministic."""
        # First build comparison
        build_dir = tmp_path / "comparison"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "build_research_comparison_analytics.py"),
                "--bundle", f"baseline={FIXTURES / 'artifact_browser_baseline'}",
                "--bundle", f"candidate={FIXTURES / 'artifact_browser_candidate_improved'}",
                "--output-dir", str(build_dir),
                "--strict",
                "--release-hold", "HOLD",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        )

        # Render twice
        out1 = tmp_path / "render1"
        out2 = tmp_path / "render2"
        for out in (out1, out2):
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "render_research_comparison_report.py"),
                    "--comparison-dir", str(build_dir),
                    "--output-dir", str(out),
                ],
                capture_output=True, text=True, cwd=str(ROOT),
                env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
            )

        md1 = (out1 / "research_comparison_report.md").read_text()
        md2 = (out2 / "research_comparison_report.md").read_text()
        assert md1 == md2

        html1 = (out1 / "research_comparison_report.html").read_text()
        html2 = (out2 / "research_comparison_report.html").read_text()
        assert html1 == html2
