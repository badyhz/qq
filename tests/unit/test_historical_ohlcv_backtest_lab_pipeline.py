"""Tests for historical OHLCV backtest lab pipeline CLI (Phase 18)."""
from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import pytest

from scripts.run_historical_ohlcv_backtest_lab import (
    _step_comparison,
    _step_data_quality,
    _step_matrix_evaluation,
    _step_matrix_generation,
    _step_render_reports,
    _step_scorecard,
    main,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def _sample_csv_rows(n: int = 50) -> list[list[str]]:
    header = ["timestamp", "open", "high", "low", "close", "volume"]
    rows = [header]
    base_ts = 1000000
    base_price = 100.0
    for i in range(n):
        ts = base_ts + i * 300
        o = base_price + i * 0.1
        h = o + 0.5
        l = o - 0.3
        c = o + 0.2
        v = 1000.0 + i
        rows.append([str(ts), f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", f"{v:.2f}"])
    return rows


def _create_fixture_dir(tmp_path: Path, symbols=None, timeframes=None) -> Path:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    symbols = symbols or ["BTCUSDT"]
    timeframes = timeframes or ["5m"]
    rows = _sample_csv_rows(60)
    for sym in symbols:
        for tf in timeframes:
            _write_csv(fixture_dir / f"{sym}_{tf}.csv", rows)
    return fixture_dir


# ---------------------------------------------------------------------------
# _step_data_quality tests
# ---------------------------------------------------------------------------

class TestStepDataQuality:
    def test_clean_data(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        report, all_clean = _step_data_quality(fixture_dir, ["BTCUSDT"], ["5m"], 500)
        assert all_clean is True
        assert report["dataset_count"] == 1
        assert report["quality_reports"][0]["is_clean"] is True

    def test_missing_csv(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()
        report, all_clean = _step_data_quality(fixture_dir, ["BTCUSDT"], ["5m"], 500)
        assert all_clean is False
        assert report["quality_reports"][0]["status"] == "missing"

    def test_multiple_symbols(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path, symbols=["BTCUSDT", "ETHUSDT"])
        report, all_clean = _step_data_quality(
            fixture_dir, ["BTCUSDT", "ETHUSDT"], ["5m"], 500
        )
        assert report["dataset_count"] == 2

    def test_multiple_timeframes(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path, timeframes=["5m", "15m"])
        report, all_clean = _step_data_quality(
            fixture_dir, ["BTCUSDT"], ["5m", "15m"], 500
        )
        assert report["dataset_count"] == 2

    def test_duplicate_timestamps_detected(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()
        rows = [["timestamp", "open", "high", "low", "close", "volume"]]
        for _ in range(10):
            rows.append(["1000000", "100", "101", "99", "100.5", "1000"])
        _write_csv(fixture_dir / "BTCUSDT_5m.csv", rows)
        report, all_clean = _step_data_quality(fixture_dir, ["BTCUSDT"], ["5m"], 500)
        assert all_clean is False
        assert report["quality_reports"][0]["duplicate_count"] > 0


# ---------------------------------------------------------------------------
# _step_matrix_generation tests
# ---------------------------------------------------------------------------

class TestStepMatrixGeneration:
    def test_cell_count(self):
        matrix = _step_matrix_generation(["BTCUSDT"], ["5m"], "walk_forward", ["conservative"])
        assert matrix["cell_count"] == 1

    def test_multiple_combinations(self):
        matrix = _step_matrix_generation(
            ["BTCUSDT", "ETHUSDT"], ["5m", "15m"], "walk_forward", ["conservative", "balanced"]
        )
        assert matrix["cell_count"] == 2 * 2 * 2  # 8

    def test_split_mode_preserved(self):
        matrix = _step_matrix_generation(["BTCUSDT"], ["5m"], "train_only", ["conservative"])
        assert matrix["split_mode"] == "train_only"

    def test_cells_have_required_fields(self):
        matrix = _step_matrix_generation(["BTCUSDT"], ["5m"], "walk_forward", ["conservative"])
        cell = matrix["cells"][0]
        assert "cell_id" in cell
        assert "symbol" in cell
        assert "timeframe" in cell
        assert "param_label" in cell


# ---------------------------------------------------------------------------
# _step_matrix_evaluation tests
# ---------------------------------------------------------------------------

class TestStepMatrixEvaluation:
    def test_evaluates_cells(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        matrix = _step_matrix_generation(["BTCUSDT"], ["5m"], "walk_forward", ["conservative"])
        results = _step_matrix_evaluation(matrix, fixture_dir, 500)
        assert len(results) == 1
        assert results[0]["status"] == "evaluated"

    def test_missing_data_status(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()
        matrix = _step_matrix_generation(["MISSING"], ["5m"], "walk_forward", ["conservative"])
        results = _step_matrix_evaluation(matrix, fixture_dir, 500)
        assert results[0]["status"] == "missing_data"

    def test_metrics_populated(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        matrix = _step_matrix_generation(["BTCUSDT"], ["5m"], "walk_forward", ["conservative"])
        results = _step_matrix_evaluation(matrix, fixture_dir, 500)
        metrics = results[0]["metrics"]
        assert "candidate_count" in metrics
        assert "win_rate" in metrics


# ---------------------------------------------------------------------------
# _step_scorecard tests
# ---------------------------------------------------------------------------

class TestStepScorecard:
    def test_scorecard_grades(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        matrix = _step_matrix_generation(["BTCUSDT"], ["5m"], "walk_forward", ["conservative"])
        results = _step_matrix_evaluation(matrix, fixture_dir, 500)
        scorecard = _step_scorecard(results)
        assert scorecard["cell_count"] == 1
        assert "pass_count" in scorecard
        assert "watch_count" in scorecard
        assert "reject_count" in scorecard

    def test_grade_fields_present(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        matrix = _step_matrix_generation(["BTCUSDT"], ["5m"], "walk_forward", ["conservative"])
        results = _step_matrix_evaluation(matrix, fixture_dir, 500)
        scorecard = _step_scorecard(results)
        cell = scorecard["cells"][0]
        assert "grade" in cell
        assert "reason_codes" in cell
        assert "blockers" in cell


# ---------------------------------------------------------------------------
# _step_comparison tests
# ---------------------------------------------------------------------------

class TestStepComparison:
    def test_comparison_returns_dict(self):
        scorecard = {
            "cells": [
                {"cell_id": "c1", "symbol": "BTCUSDT", "timeframe": "5m", "param_label": "conservative"},
            ]
        }
        result = _step_comparison(scorecard)
        assert "comparison_id" in result
        assert "experiment_ids" in result
        assert "pair_count" in result


# ---------------------------------------------------------------------------
# _step_render_reports tests
# ---------------------------------------------------------------------------

class TestStepRenderReports:
    def test_renders_all_formats(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        matrix = _step_matrix_generation(["BTCUSDT"], ["5m"], "walk_forward", ["conservative"])
        results = _step_matrix_evaluation(matrix, fixture_dir, 500)
        scorecard = _step_scorecard(results)
        reports = _step_render_reports(results, scorecard)
        assert len(reports["report_md"]) > 0
        assert len(reports["report_html"]) > 0
        assert "release_hold" in json.dumps(reports["report_json"])


# ---------------------------------------------------------------------------
# main() integration tests
# ---------------------------------------------------------------------------

class TestMainIntegration:
    def test_main_exits_zero(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path, symbols=["BTCUSDT"], timeframes=["5m"])
        output_dir = tmp_path / "output"
        rc = main([
            "--fixture-dir", str(fixture_dir),
            "--output-dir", str(output_dir),
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
            "--chunk-size", "50",
        ])
        assert rc == 0

    def test_main_writes_manifest(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        output_dir = tmp_path / "output"
        main([
            "--fixture-dir", str(fixture_dir),
            "--output-dir", str(output_dir),
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
        ])
        manifest = json.loads((output_dir / "manifest.json").read_text())
        assert manifest["release_hold"] == "HOLD"
        assert manifest["no_live"] is True

    def test_main_missing_fixture_dir_returns_1(self, tmp_path):
        rc = main([
            "--fixture-dir", "/nonexistent/path",
            "--output-dir", str(tmp_path / "output"),
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
        ])
        assert rc == 1

    def test_main_invalid_param_grid_returns_1(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        rc = main([
            "--fixture-dir", str(fixture_dir),
            "--output-dir", str(tmp_path / "output"),
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "invalid_preset",
        ])
        assert rc == 1

    def test_main_writes_all_artifacts(self, tmp_path):
        fixture_dir = _create_fixture_dir(tmp_path)
        output_dir = tmp_path / "output"
        main([
            "--fixture-dir", str(fixture_dir),
            "--output-dir", str(output_dir),
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
        ])
        expected_files = [
            "data_quality_report.json", "matrix.json", "results.json",
            "scorecard.json", "comparison.json", "report.md",
            "report.html", "report.json", "manifest.json",
        ]
        for fname in expected_files:
            assert (output_dir / fname).exists(), f"Missing {fname}"
