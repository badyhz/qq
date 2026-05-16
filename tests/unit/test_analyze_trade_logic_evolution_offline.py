from __future__ import annotations

from scripts.analyze_trade_logic_evolution_offline import (
    build_trade_features,
    normalize_trade_row,
    summarize_trade_features,
)


def test_normalize_trade_row_long() -> None:
    row = {
        "symbol": "btcusdt",
        "side": "BUY",
        "entry_price": 100.0,
        "exit_price": 110.0,
        "quantity": 2.0,
    }
    feature = normalize_trade_row(row)
    assert feature is not None
    assert feature.symbol == "BTCUSDT"
    assert feature.direction == "LONG"
    assert feature.return_pct == 10.0
    assert feature.pnl == 20.0


def test_normalize_trade_row_short() -> None:
    row = {
        "symbol": "ETHUSDT",
        "side": "SELL",
        "entry": 200.0,
        "exit": 180.0,
        "qty": 1.5,
    }
    feature = normalize_trade_row(row)
    assert feature is not None
    assert feature.direction == "SHORT"
    assert round(feature.return_pct, 6) == 10.0
    assert round(feature.pnl, 6) == 30.0


def test_build_and_summarize_filters_invalid() -> None:
    rows = [
        {"symbol": "BTCUSDT", "side": "BUY", "entry_price": 100, "exit_price": 105, "quantity": 1},
        {"symbol": "ETHUSDT", "side": "SELL", "entry_price": 100, "exit_price": 95, "quantity": 2},
        {"symbol": "", "side": "BUY", "entry_price": 10, "exit_price": 11, "quantity": 1},
        {"symbol": "SOLUSDT", "side": "BUY", "entry_price": 0, "exit_price": 11, "quantity": 1},
    ]
    features = build_trade_features(rows)
    summary = summarize_trade_features(features)

    assert len(features) == 2
    assert summary["total_trades"] == 2
    assert summary["win_rate"] == 1.0
    assert summary["long_count"] == 1
    assert summary["short_count"] == 1
