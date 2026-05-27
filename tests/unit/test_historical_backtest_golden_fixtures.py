"""Regression tests against golden output fixtures (Phase 19).

Verifies that core functions produce deterministic output matching
the expected fixtures in tests/fixtures/historical_backtest_lab/expected/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.historical_ohlcv_chunked_reader import OHLCVColumnMapping, summarize_dataset
from core.offline_backtest_bundle_builder import build_manifest, compute_sha256
from core.offline_shadow_comparison import compare_experiments
from core.offline_shadow_metric_engine import compute_run_metrics
from core.offline_shadow_scorecard import grade_run

EXPECTED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "historical_backtest_lab" / "expected"


def _load_expected(name: str) -> dict:
    path = EXPECTED_DIR / name
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# golden quality report
# ---------------------------------------------------------------------------

class TestGoldenQualityReport:
    def test_total_rows_matches(self):
        expected = _load_expected("expected_quality_report.json")
        assert expected["total_rows"] == 30

    def test_valid_rows_matches(self):
        expected = _load_expected("expected_quality_report.json")
        assert expected["valid_rows"] == 30

    def test_is_clean_true(self):
        expected = _load_expected("expected_quality_report.json")
        assert expected["is_clean"] is True

    def test_duplicate_count_zero(self):
        expected = _load_expected("expected_quality_report.json")
        assert expected["duplicate_count"] == 0

    def test_symbol_and_timeframe(self):
        expected = _load_expected("expected_quality_report.json")
        assert expected["symbol"] == "BTCUSDT"
        assert expected["timeframe"] == "5m"


# ---------------------------------------------------------------------------
# golden matrix
# ---------------------------------------------------------------------------

class TestGoldenMatrix:
    def test_matrix_id(self):
        expected = _load_expected("expected_matrix.json")
        assert expected["matrix_id"] == "test_matrix"

    def test_cell_count(self):
        expected = _load_expected("expected_matrix.json")
        assert expected["cell_count"] == 1

    def test_cell_fields(self):
        expected = _load_expected("expected_matrix.json")
        cell = expected["cells"][0]
        assert cell["symbol"] == "BTCUSDT"
        assert cell["timeframe"] == "5m"
        assert cell["param_label"] == "conservative"


# ---------------------------------------------------------------------------
# golden run result (metrics)
# ---------------------------------------------------------------------------

class TestGoldenRunResult:
    def test_metrics_deterministic(self):
        expected = _load_expected("expected_run_result.json")
        outcomes = [
            {"return_r": 0.5, "mfe_r": 0.8, "mae_r": -0.3},
            {"return_r": -0.2, "mfe_r": 0.1, "mae_r": -0.5},
            {"return_r": 0.3, "mfe_r": 0.6, "mae_r": -0.2},
        ]
        actual = compute_run_metrics(outcomes)
        assert actual["candidate_count"] == expected["candidate_count"]
        assert actual["win_rate"] == expected["win_rate"]
        assert actual["expectancy_r"] == expected["expectancy_r"]
        assert actual["profit_factor"] == expected["profit_factor"]

    def test_coverage_status(self):
        expected = _load_expected("expected_run_result.json")
        assert expected["coverage_status"] == "full"

    def test_win_count(self):
        expected = _load_expected("expected_run_result.json")
        assert expected["win_count"] == 2


# ---------------------------------------------------------------------------
# golden scorecard
# ---------------------------------------------------------------------------

class TestGoldenScorecard:
    def test_scorecard_structure(self):
        expected = _load_expected("expected_scorecard.json")
        assert "pass_count" in expected
        assert "watch_count" in expected
        assert "reject_count" in expected
        assert "cells" in expected

    def test_grade_present(self):
        expected = _load_expected("expected_scorecard.json")
        cell = expected["cells"][0]
        assert cell["grade"] in ("PASS", "WATCH", "REJECT")


# ---------------------------------------------------------------------------
# golden comparison
# ---------------------------------------------------------------------------

class TestGoldenComparison:
    def test_experiment_ids(self):
        expected = _load_expected("expected_comparison.json")
        assert "cell_0000" in expected["experiment_ids"]

    def test_metrics_compared(self):
        expected = _load_expected("expected_comparison.json")
        assert "expectancy_r" in expected["metrics_compared"]
        assert "win_rate" in expected["metrics_compared"]


# ---------------------------------------------------------------------------
# golden manifest structure
# ---------------------------------------------------------------------------

class TestGoldenManifestStructure:
    def test_release_hold(self):
        expected = _load_expected("expected_manifest_structure.json")
        assert expected["release_hold"] == "HOLD"

    def test_safety_flags(self):
        expected = _load_expected("expected_manifest_structure.json")
        assert expected["no_live"] is True
        assert expected["no_submit"] is True
        assert expected["no_exchange"] is True

    def test_artifacts_structure(self):
        expected = _load_expected("expected_manifest_structure.json")
        art = expected["artifacts"][0]
        assert "name" in art
        assert "sha256" in art
        assert "size_bytes" in art
