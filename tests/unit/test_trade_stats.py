import csv
import math
from pathlib import Path

import pytest

from core.trade_stats import load_trade_rows, summarize_trade_stats


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    return tmp_path / "trades.csv"


def write_rows(csv_path: Path, rows: list[dict]) -> None:
    fieldnames = ["trade_id", "status", "net_pnl"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_summarize_trade_stats_with_empty_data():
    stats = summarize_trade_stats([])

    assert stats["total_trades"] == 0
    assert stats["closed_trades"] == 0
    assert stats["win_trades"] == 0
    assert stats["loss_trades"] == 0
    assert stats["win_rate"] == pytest.approx(0.0)
    assert stats["gross_profit"] == pytest.approx(0.0)
    assert stats["gross_loss"] == pytest.approx(0.0)
    assert stats["net_profit"] == pytest.approx(0.0)
    assert stats["average_pnl"] == pytest.approx(0.0)
    assert stats["average_win"] == pytest.approx(0.0)
    assert stats["average_loss"] == pytest.approx(0.0)
    assert stats["profit_factor"] == pytest.approx(0.0)
    assert stats["expectancy"] == pytest.approx(0.0)
    assert stats["max_win"] == pytest.approx(0.0)
    assert stats["max_loss"] == pytest.approx(0.0)
    assert stats["max_consecutive_wins"] == 0
    assert stats["max_consecutive_losses"] == 0
    assert stats["equity_curve"] == []
    assert stats["peak_equity"] == pytest.approx(0.0)
    assert stats["max_drawdown"] == pytest.approx(0.0)
    assert stats["max_drawdown_pct"] == pytest.approx(0.0)
    assert stats["fee_total"] == pytest.approx(0.0)
    assert stats["avg_fee_per_trade"] == pytest.approx(0.0)
    assert stats["expectancy_long"] == pytest.approx(0.0)
    assert stats["expectancy_short"] == pytest.approx(0.0)
    assert stats["avg_holding_seconds"] == pytest.approx(0.0)
    assert stats["pnl_std"] == pytest.approx(0.0)


def test_summarize_trade_stats_with_single_winning_trade():
    stats = summarize_trade_stats([{"trade_id": "1", "status": "CLOSED", "net_pnl": 12.5}])

    assert stats["total_trades"] == 1
    assert stats["closed_trades"] == 1
    assert stats["win_trades"] == 1
    assert stats["loss_trades"] == 0
    assert stats["win_rate"] == pytest.approx(1.0)
    assert stats["gross_profit"] == pytest.approx(12.5)
    assert stats["gross_loss"] == pytest.approx(0.0)
    assert stats["net_profit"] == pytest.approx(12.5)
    assert stats["average_pnl"] == pytest.approx(12.5)
    assert stats["average_win"] == pytest.approx(12.5)
    assert stats["average_loss"] == pytest.approx(0.0)
    assert math.isinf(stats["profit_factor"])
    assert stats["expectancy"] == pytest.approx(12.5)
    assert stats["max_win"] == pytest.approx(12.5)
    assert stats["max_loss"] == pytest.approx(12.5)
    assert stats["max_consecutive_wins"] == 1
    assert stats["max_consecutive_losses"] == 0


def test_summarize_trade_stats_with_mixed_results():
    trades = [
        {"trade_id": "1", "status": "CLOSED", "net_pnl": 10.0, "side": "LONG", "total_cost": 1.5},
        {"trade_id": "2", "status": "CLOSED", "net_pnl": -4.0, "side": "SHORT", "fees_total": 1.0},
        {"trade_id": "3", "status": "CLOSED", "net_pnl": 6.0, "side": "LONG", "holding_seconds": 120},
        {"trade_id": "4", "status": "OPEN", "net_pnl": 100.0},
    ]

    stats = summarize_trade_stats(trades)

    assert stats["total_trades"] == 4
    assert stats["closed_trades"] == 3
    assert stats["win_trades"] == 2
    assert stats["loss_trades"] == 1
    assert stats["win_rate"] == pytest.approx(2 / 3)
    assert stats["gross_profit"] == pytest.approx(16.0)
    assert stats["gross_loss"] == pytest.approx(-4.0)
    assert stats["net_profit"] == pytest.approx(12.0)
    assert stats["average_pnl"] == pytest.approx(4.0)
    assert stats["average_win"] == pytest.approx(8.0)
    assert stats["average_loss"] == pytest.approx(-4.0)
    assert stats["profit_factor"] == pytest.approx(4.0)
    assert stats["expectancy"] == pytest.approx((2 / 3) * 8.0 + (1 / 3) * -4.0)
    assert stats["max_win"] == pytest.approx(10.0)
    assert stats["max_loss"] == pytest.approx(-4.0)
    assert stats["equity_curve"] == pytest.approx([10.0, 6.0, 12.0])
    assert stats["peak_equity"] == pytest.approx(12.0)
    assert stats["max_drawdown"] == pytest.approx(4.0)
    assert stats["max_drawdown_pct"] == pytest.approx(0.4)
    assert stats["fee_total"] == pytest.approx(2.5)
    assert stats["avg_fee_per_trade"] == pytest.approx(2.5 / 3)
    assert stats["expectancy_long"] == pytest.approx(8.0)
    assert stats["expectancy_short"] == pytest.approx(-4.0)
    assert stats["avg_holding_seconds"] == pytest.approx(120.0)
    assert stats["pnl_std"] == pytest.approx(math.sqrt((36.0 + 64.0 + 4.0) / 3))


def test_summarize_trade_stats_computes_consecutive_streaks():
    trades = [
        {"trade_id": "1", "status": "CLOSED", "net_pnl": 5.0},
        {"trade_id": "2", "status": "CLOSED", "net_pnl": 4.0},
        {"trade_id": "3", "status": "CLOSED", "net_pnl": -1.0},
        {"trade_id": "4", "status": "CLOSED", "net_pnl": -2.0},
        {"trade_id": "5", "status": "CLOSED", "net_pnl": -3.0},
        {"trade_id": "6", "status": "CLOSED", "net_pnl": 7.0},
    ]

    stats = summarize_trade_stats(trades)

    assert stats["max_consecutive_wins"] == 2
    assert stats["max_consecutive_losses"] == 3


def test_summarize_trade_stats_ignores_open_trades_and_handles_csv(csv_path: Path):
    write_rows(
        csv_path,
        [
            {"trade_id": "1", "status": "OPEN", "net_pnl": "99.0"},
            {"trade_id": "2", "status": "CLOSED", "net_pnl": "3.0"},
            {"trade_id": "3", "status": "CLOSED", "net_pnl": "-1.0"},
        ],
    )

    rows = load_trade_rows(csv_path)
    stats = summarize_trade_stats(csv_path)

    assert len(rows) == 3
    assert stats["total_trades"] == 3
    assert stats["closed_trades"] == 2
    assert stats["net_profit"] == pytest.approx(2.0)
    assert stats["win_trades"] == 1
    assert stats["loss_trades"] == 1


def test_summarize_trade_stats_handles_zero_gross_loss_safely():
    stats = summarize_trade_stats(
        [
            {"trade_id": "1", "status": "CLOSED", "net_pnl": 3.0},
            {"trade_id": "2", "status": "CLOSED", "net_pnl": 2.0},
        ]
    )

    assert math.isinf(stats["profit_factor"])


def test_summarize_trade_stats_handles_missing_csv_path(tmp_path: Path):
    stats = summarize_trade_stats(tmp_path / "missing.csv")

    assert stats["total_trades"] == 0
    assert stats["closed_trades"] == 0
    assert stats["net_profit"] == pytest.approx(0.0)


def test_summarize_trade_stats_handles_empty_csv_file(csv_path: Path):
    csv_path.write_text("", encoding="utf-8")

    stats = summarize_trade_stats(csv_path)

    assert stats["total_trades"] == 0
    assert stats["closed_trades"] == 0
    assert stats["win_rate"] == pytest.approx(0.0)


def test_summarize_trade_stats_handles_open_only_rows(csv_path: Path):
    write_rows(
        csv_path,
        [
            {"trade_id": "1", "status": "OPEN", "net_pnl": "5.0"},
            {"trade_id": "2", "status": "OPEN", "net_pnl": "-2.0"},
        ],
    )

    stats = summarize_trade_stats(csv_path)

    assert stats["total_trades"] == 2
    assert stats["closed_trades"] == 0
    assert stats["win_trades"] == 0
    assert stats["loss_trades"] == 0
    assert stats["net_profit"] == pytest.approx(0.0)


def test_summarize_trade_stats_handles_missing_non_critical_fields(csv_path: Path):
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["exit_time", "pnl"])
        writer.writeheader()
        writer.writerow({"exit_time": "2026-04-19T10:00:00+00:00", "pnl": "6.0"})
        writer.writerow({"exit_time": "2026-04-19T10:05:00+00:00", "pnl": "-2.5"})

    stats = summarize_trade_stats(csv_path)

    assert stats["total_trades"] == 2
    assert stats["closed_trades"] == 2
    assert stats["win_trades"] == 1
    assert stats["loss_trades"] == 1
    assert stats["net_profit"] == pytest.approx(3.5)


def test_summarize_trade_stats_computes_drawdown_from_equity_curve():
    stats = summarize_trade_stats(
        [
            {"trade_id": "1", "status": "CLOSED", "net_pnl": 10.0},
            {"trade_id": "2", "status": "CLOSED", "net_pnl": -5.0},
            {"trade_id": "3", "status": "CLOSED", "net_pnl": 3.0},
            {"trade_id": "4", "status": "CLOSED", "net_pnl": -8.0},
        ]
    )

    assert stats["equity_curve"] == pytest.approx([10.0, 5.0, 8.0, 0.0])
    assert stats["peak_equity"] == pytest.approx(10.0)
    assert stats["max_drawdown"] == pytest.approx(10.0)
    assert stats["max_drawdown_pct"] == pytest.approx(1.0)


def test_summarize_trade_stats_computes_expectancy_by_side():
    stats = summarize_trade_stats(
        [
            {"trade_id": "1", "status": "CLOSED", "side": "LONG", "net_pnl": 5.0},
            {"trade_id": "2", "status": "CLOSED", "side": "LONG", "net_pnl": -1.0},
            {"trade_id": "3", "status": "CLOSED", "side": "SHORT", "net_pnl": 4.0},
            {"trade_id": "4", "status": "CLOSED", "side": "SHORT", "net_pnl": -2.0},
            {"trade_id": "5", "status": "OPEN", "side": "SHORT", "net_pnl": 100.0},
        ]
    )

    assert stats["expectancy_long"] == pytest.approx(2.0)
    assert stats["expectancy_short"] == pytest.approx(1.0)


def test_summarize_trade_stats_holding_seconds_missing_is_safe():
    stats = summarize_trade_stats(
        [
            {"trade_id": "1", "status": "CLOSED", "net_pnl": 2.0},
            {"trade_id": "2", "status": "CLOSED", "net_pnl": 3.0, "holding_seconds": 30},
        ]
    )

    assert stats["avg_holding_seconds"] == pytest.approx(30.0)


def test_summarize_trade_stats_without_closed_data_returns_safe_risk_metrics():
    stats = summarize_trade_stats(
        [
            {"trade_id": "1", "status": "OPEN", "net_pnl": 3.0},
            {"trade_id": "2", "status": "OPEN", "net_pnl": -2.0},
        ]
    )

    assert stats["closed_trades"] == 0
    assert stats["equity_curve"] == []
    assert stats["max_drawdown"] == pytest.approx(0.0)
    assert stats["max_drawdown_pct"] == pytest.approx(0.0)
    assert stats["fee_total"] == pytest.approx(0.0)
    assert stats["expectancy_long"] == pytest.approx(0.0)
    assert stats["expectancy_short"] == pytest.approx(0.0)
