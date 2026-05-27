"""Tests for scripts/evaluate_historical_backtest_matrix.py — 10+ tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure repo root on path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.evaluate_historical_backtest_matrix import (
    _evaluate_single_run,
    evaluate_matrix,
    main,
    parse_args,
)


@pytest.fixture
def tmp_matrix(tmp_path):
    """Create a minimal matrix JSON file."""
    matrix = [
        {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "param_id": "P1",
            "trades": [
                {
                    "trade_id": "T1", "signal_id": "S1",
                    "entry_bar_index": 0, "exit_bar_index": 10,
                    "entry_price": 100.0, "exit_price": 105.0,
                    "exit_reason": "TP", "realized_r": 2.0,
                    "gross_pnl": 5.0, "fees": 0.1, "slippage_cost": 0.05,
                    "net_pnl": 4.85, "mfe_r": 2.5, "mae_r": -0.3,
                    "hold_bars": 10,
                },
            ] * 15,
        },
    ]
    p = tmp_path / "matrix.json"
    p.write_text(json.dumps(matrix))
    return str(p)


@pytest.fixture
def tmp_empty_matrix(tmp_path):
    p = tmp_path / "empty_matrix.json"
    p.write_text(json.dumps([]))
    return str(p)


class TestParseArgs:
    def test_required_arg(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_matrix_json_required(self):
        ns = parse_args(["--matrix-json", "test.json"])
        assert ns.matrix_json == "test.json"

    def test_defaults(self):
        ns = parse_args(["--matrix-json", "x.json"])
        assert ns.fixture_dir == "."
        assert ns.output_json is None
        assert ns.output_md is None

    def test_all_args(self):
        ns = parse_args([
            "--matrix-json", "m.json",
            "--fixture-dir", "fd",
            "--output-json", "o.json",
            "--output-md", "o.md",
        ])
        assert ns.fixture_dir == "fd"
        assert ns.output_json == "o.json"
        assert ns.output_md == "o.md"


class TestEvaluateSingleRun:
    def test_basic_run(self, tmp_path):
        cfg = {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "param_id": "P1",
            "trades": [
                {
                    "trade_id": "T1", "signal_id": "S1",
                    "entry_bar_index": 0, "exit_bar_index": 10,
                    "entry_price": 100.0, "exit_price": 105.0,
                    "exit_reason": "TP", "realized_r": 1.0,
                    "gross_pnl": 5.0, "fees": 0.1, "slippage_cost": 0.05,
                    "net_pnl": 4.85, "mfe_r": 1.5, "mae_r": -0.3,
                    "hold_bars": 10,
                },
            ] * 12,
        }
        result = _evaluate_single_run(cfg, tmp_path, 0)
        assert result["symbol"] == "BTCUSDT"
        assert result["param_id"] == "P1"
        assert result["grade"] == "PASS"
        assert result["metrics"]["trade_count"] == 12

    def test_no_trades(self, tmp_path):
        cfg = {"symbol": "X", "timeframe": "1h"}
        result = _evaluate_single_run(cfg, tmp_path, 0)
        assert result["grade"] == "INSUFFICIENT_SAMPLE"


class TestEvaluateMatrix:
    def test_empty_matrix(self, tmp_path):
        result = evaluate_matrix([], tmp_path)
        assert len(result["run_results"]) == 0
        assert result["aggregate"]["run_count"] == 0

    def test_with_trades(self, tmp_path):
        matrix = [
            {
                "symbol": "BTCUSDT", "timeframe": "1h", "param_id": "P1",
                "trades": [
                    {
                        "trade_id": f"T{i}", "signal_id": f"S{i}",
                        "entry_bar_index": i * 10, "exit_bar_index": i * 10 + 10,
                        "entry_price": 100.0, "exit_price": 105.0,
                        "exit_reason": "TP", "realized_r": 1.0,
                        "gross_pnl": 5.0, "fees": 0.1, "slippage_cost": 0.05,
                        "net_pnl": 4.85, "mfe_r": 1.5, "mae_r": -0.3,
                        "hold_bars": 10,
                    }
                    for i in range(15)
                ],
            },
        ]
        result = evaluate_matrix(matrix, tmp_path)
        assert len(result["run_results"]) == 1
        assert result["aggregate"]["total_trades"] == 15

    def test_rejection_reasons_collected(self, tmp_path):
        matrix = [
            {
                "symbol": "X", "timeframe": "1h",
                "trades": [],  # insufficient sample
            },
        ]
        result = evaluate_matrix(matrix, tmp_path)
        assert len(result["rejection_reasons"]) == 1
        assert result["rejection_reasons"][0]["grade"] == "INSUFFICIENT_SAMPLE"


class TestMainCLI:
    def test_missing_file(self, tmp_path):
        rc = main(["--matrix-json", str(tmp_path / "nope.json")])
        assert rc == 1

    def test_success(self, tmp_matrix, tmp_path):
        out_json = str(tmp_path / "out.json")
        rc = main(["--matrix-json", tmp_matrix, "--output-json", out_json])
        assert rc == 0
        assert Path(out_json).exists()

    def test_output_json_content(self, tmp_matrix, tmp_path):
        out_json = str(tmp_path / "out.json")
        main(["--matrix-json", tmp_matrix, "--output-json", out_json])
        with open(out_json) as f:
            data = json.load(f)
        assert "run_results" in data
        assert "aggregate" in data

    def test_output_md(self, tmp_matrix, tmp_path):
        out_md = str(tmp_path / "out.md")
        out_json = str(tmp_path / "out2.json")
        rc = main([
            "--matrix-json", tmp_matrix,
            "--output-json", out_json,
            "--output-md", out_md,
        ])
        assert rc == 0
        assert Path(out_md).exists()
        content = Path(out_md).read_text()
        assert "HOLD" in content
