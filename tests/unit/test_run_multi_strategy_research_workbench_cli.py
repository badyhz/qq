"""Tests for full pipeline CLI — T4921-T4950."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE_DIR = "tests/fixtures/historical_backtest_lab"


class TestFullPipelineCLI:
    def test_full_pipeline_runs(self, tmp_path):
        import subprocess
        result = subprocess.run(
            [
                "python3", "scripts/run_multi_strategy_research_workbench.py",
                "--fixture-dir", FIXTURE_DIR,
                "--output-dir", str(tmp_path),
                "--strategies", "breakout",
                "--symbols", "BTCUSDT",
                "--timeframes", "5m",
                "--split-mode", "rolling",
                "--search-budget", "20",
                "--chunk-size", "25",
            ],
            capture_output=True, text=True, timeout=60,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}\nstdout: {result.stdout}"

        # Verify artifacts
        required = [
            "strategy_registry.json", "parameter_search.json", "matrix.json",
            "results.json", "portfolio_summary.json", "comparison.json",
            "promotion_recommendations.json", "artifact_index.json",
            "report.md", "report.html", "manifest.json",
        ]
        for name in required:
            assert (tmp_path / name).exists(), f"missing {name}"

        # Verify manifest
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert manifest["release_hold"] == "HOLD"
        assert manifest["no_live"] is True
        assert manifest["no_submit"] is True
        assert manifest["no_exchange"] is True

    def test_multi_strategy_pipeline(self, tmp_path):
        import subprocess
        result = subprocess.run(
            [
                "python3", "scripts/run_multi_strategy_research_workbench.py",
                "--fixture-dir", FIXTURE_DIR,
                "--output-dir", str(tmp_path),
                "--strategies", "breakout,mean_reversion",
                "--symbols", "BTCUSDT,ETHUSDT",
                "--timeframes", "5m,15m",
                "--split-mode", "rolling",
                "--search-budget", "30",
                "--chunk-size", "25",
            ],
            capture_output=True, text=True, timeout=120,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        registry = json.loads((tmp_path / "strategy_registry.json").read_text())
        assert registry["strategy_count"] == 2

    def test_invalid_strategy_fails(self, tmp_path):
        import subprocess
        result = subprocess.run(
            [
                "python3", "scripts/run_multi_strategy_research_workbench.py",
                "--fixture-dir", FIXTURE_DIR,
                "--output-dir", str(tmp_path),
                "--strategies", "nonexistent_strategy",
                "--symbols", "BTCUSDT",
                "--timeframes", "5m",
                "--search-budget", "10",
                "--chunk-size", "25",
            ],
            capture_output=True, text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode != 0
