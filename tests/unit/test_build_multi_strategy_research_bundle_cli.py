"""Tests for build bundle CLI — T4891-T4920."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.research_artifact_index import build_artifact_index, validate_artifact_index
from core.research_workbench_manifest import build_manifest, validate_manifest


class TestBundleBuild:
    def test_builds_from_empty_dir(self, tmp_path):
        """Bundle builder should handle empty dir gracefully."""
        import subprocess
        result = subprocess.run(
            [
                "python3", "scripts/build_multi_strategy_research_bundle.py",
                "--input-dir", str(tmp_path),
                "--output-dir", str(tmp_path / "out"),
            ],
            capture_output=True, text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

    def test_builds_with_artifacts(self, tmp_path):
        """Build bundle from a directory with artifacts."""
        (tmp_path / "strategy_registry.json").write_text(json.dumps({
            "strategy_count": 1, "validation_status": "PASS",
            "release_hold": "HOLD", "safety_flags": {},
        }))
        (tmp_path / "results.json").write_text(json.dumps({
            "total_rows": 1, "evaluated_rows": 1, "skipped_rows": 0,
            "results": [{
                "run_result_id": "r1", "matrix_row_id": "row1",
                "strategy_id": "breakout", "symbol": "BTCUSDT", "timeframe": "5m",
                "split_id": "s0", "parameter_set_id": "ps0", "data_quality": {},
                "signal_count": 10, "trade_count": 10, "win_rate": 0.6,
                "expectancy_r": 0.2, "avg_return": 0.01, "max_drawdown": 0.05,
                "profit_factor": 1.5, "avg_mfe": 0.03, "avg_mae": 0.01,
                "score": 0.6, "warnings": [], "release_hold": "HOLD",
            }],
        }))

        import subprocess
        result = subprocess.run(
            [
                "python3", "scripts/build_multi_strategy_research_bundle.py",
                "--input-dir", str(tmp_path),
                "--output-dir", str(tmp_path),
            ],
            capture_output=True, text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode == 0
        assert (tmp_path / "artifact_index.json").exists()
        assert (tmp_path / "manifest.json").exists()
        assert (tmp_path / "report.md").exists()
        assert (tmp_path / "report.html").exists()

    def test_manifest_valid(self, tmp_path):
        m = build_manifest(tmp_path)
        errors = validate_manifest(m)
        assert errors == []

    def test_artifact_index_valid(self, tmp_path):
        (tmp_path / "manifest.json").write_text("{}")
        index = build_artifact_index(tmp_path)
        errors = validate_artifact_index(index)
        assert errors == []
