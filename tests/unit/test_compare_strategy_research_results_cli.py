"""Tests for strategy comparison CLI — T4771-T4800."""
from __future__ import annotations

import json

import pytest

from core.multi_strategy_comparison import (
    StrategyComparisonResult,
    compare_strategies,
    comparison_to_dict,
)
from core.multi_strategy_evaluator import RunResult


def _make_result(sid="breakout", symbol="BTCUSDT", score=0.5):
    return RunResult(
        run_result_id=f"r_{sid}", matrix_row_id=f"row_{sid}",
        strategy_id=sid, symbol=symbol, timeframe="5m",
        split_id="s0", parameter_set_id="ps0", data_quality={},
        signal_count=10, trade_count=10, win_rate=score,
        expectancy_r=score, avg_return=score * 0.02, max_drawdown=0.05,
        profit_factor=1.5, avg_mfe=0.03, avg_mae=0.01, score=score, warnings=[],
    )


class TestComparison:
    def test_empty(self):
        comp = compare_strategies([])
        assert len(comp.strategy_rankings) == 0

    def test_rankings(self):
        results = [_make_result("breakout", score=0.6), _make_result("momentum", score=0.8)]
        comp = compare_strategies(results)
        assert len(comp.strategy_rankings) == 2
        assert comp.strategy_rankings[0]["strategy_id"] == "momentum"

    def test_family_summary(self):
        results = [_make_result("breakout"), _make_result("momentum")]
        comp = compare_strategies(results)
        assert "breakout" in comp.family_summary

    def test_timeframe_summary(self):
        results = [_make_result()]
        comp = compare_strategies(results)
        assert "5m" in comp.timeframe_summary

    def test_symbol_summary(self):
        results = [_make_result(symbol="BTCUSDT"), _make_result(symbol="ETHUSDT")]
        comp = compare_strategies(results)
        assert "BTCUSDT" in comp.symbol_summary

    def test_deterministic(self):
        results = [_make_result("breakout"), _make_result("momentum")]
        c1 = comparison_to_dict(compare_strategies(results))
        c2 = comparison_to_dict(compare_strategies(results))
        assert json.dumps(c1, sort_keys=True) == json.dumps(c2, sort_keys=True)


class TestComparisonCLI:
    def test_cli_runs(self, tmp_path):
        import subprocess
        # Create results file
        results = {
            "total_rows": 2, "evaluated_rows": 2, "skipped_rows": 0,
            "results": [
                {
                    "run_result_id": "r1", "matrix_row_id": "row1",
                    "strategy_id": "breakout", "symbol": "BTCUSDT", "timeframe": "5m",
                    "split_id": "s0", "parameter_set_id": "ps0", "data_quality": {},
                    "signal_count": 10, "trade_count": 10, "win_rate": 0.6,
                    "expectancy_r": 0.2, "avg_return": 0.01, "max_drawdown": 0.05,
                    "profit_factor": 1.5, "avg_mfe": 0.03, "avg_mae": 0.01,
                    "score": 0.6, "warnings": [], "release_hold": "HOLD",
                },
            ],
        }
        results_path = tmp_path / "results.json"
        results_path.write_text(json.dumps(results, sort_keys=True))

        result = subprocess.run(
            [
                "python3", "scripts/compare_strategy_research_results.py",
                "--results", str(results_path),
                "--output-dir", str(tmp_path),
            ],
            capture_output=True, text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert (tmp_path / "comparison.json").exists()
        assert (tmp_path / "promotion_recommendations.json").exists()
