from __future__ import annotations

from scripts.right_breakout_scan_common import (
    build_param_grid,
    build_scan_grid,
    parse_symbols,
    parse_timeframes,
    summarize_scan_results,
)


def test_parse_symbols() -> None:
    assert parse_symbols("btcusdt, ethusdt ,,SOLUSDT") == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def test_parse_timeframes() -> None:
    assert parse_timeframes("5m,15m,2m,1h") == ["5m", "15m", "1h"]


def test_build_scan_grid() -> None:
    grid = build_scan_grid(["BTCUSDT"], ["5m", "15m"], [60, 70], [20])
    assert len(grid) == 4
    assert grid[0]["symbol"] == "BTCUSDT"
    assert grid[0]["lookback"] == 20


def test_build_param_grid() -> None:
    grid = build_param_grid({"a": [1, 2], "b": ["x"]})
    assert grid == [{"a": 1, "b": "x"}, {"a": 2, "b": "x"}]


def test_summarize_scan_results() -> None:
    summary = summarize_scan_results(
        [
            {"symbol": "BTCUSDT", "accepted": True, "score": 80},
            {"symbol": "ETHUSDT", "accepted": False, "score": 60},
            {"symbol": "ETHUSDT", "accepted": True, "score": 70},
        ]
    )
    assert summary["total"] == 3
    assert summary["accepted"] == 2
    assert summary["rejected"] == 1
    assert summary["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert summary["avg_score"] == 70.0
