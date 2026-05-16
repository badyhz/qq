import csv
from pathlib import Path

import dashboard
from core.trade_logger import TradeRecord, append_trade, update_trade


def _write_rows(csv_path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "trade_id",
        "symbol",
        "status",
        "pnl",
        "score",
        "strategy_profile",
        "reward_risk_ratio",
        "mae_pct",
        "mfe_pct",
        "exit_reason",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_trade_dashboard_run_handles_missing_csv(tmp_path: Path, capsys) -> None:
    view = dashboard.TradeDashboard(str(tmp_path / "missing.csv"))
    view.run()

    output = capsys.readouterr().out
    assert "No trade data yet" in output


def test_trade_dashboard_run_prints_sections(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "trades.csv"
    _write_rows(
        csv_path,
        [
            {
                "trade_id": "1",
                "symbol": "BTCUSDT",
                "status": "CLOSED",
                "pnl": "12.0",
                "score": "3",
                "strategy_profile": "baseline",
                "reward_risk_ratio": "2.1",
                "mae_pct": "0.01",
                "mfe_pct": "0.03",
                "exit_reason": "TAKE_PROFIT",
            },
            {
                "trade_id": "2",
                "symbol": "BTCUSDT",
                "status": "CLOSED",
                "pnl": "-3.0",
                "score": "2",
                "strategy_profile": "baseline",
                "reward_risk_ratio": "1.3",
                "mae_pct": "0.02",
                "mfe_pct": "0.01",
                "exit_reason": "STOP_LOSS",
            },
            {
                "trade_id": "3",
                "symbol": "ETHUSDT",
                "status": "OPEN",
                "pnl": "0.0",
                "score": "1",
                "strategy_profile": "aggressive",
                "reward_risk_ratio": "1.1",
                "mae_pct": "0.01",
                "mfe_pct": "0.01",
                "exit_reason": "",
            },
        ],
    )

    view = dashboard.TradeDashboard(str(csv_path))
    view.run()
    output = capsys.readouterr().out

    assert "=== Global Performance ===" in output
    assert "=== Score Breakdown ===" in output
    assert "=== Symbol Breakdown ===" in output
    assert "=== Strategy Profiles ===" in output
    assert "=== Exit Reasons ===" in output
    assert "Total Trades" in output
    assert "Net PnL" in output


def test_trade_dashboard_chain_from_trade_logger_csv(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "trades.csv"

    append_trade(
        csv_path,
        TradeRecord(
            trade_id="A-1",
            symbol="BTCUSDT",
            side="LONG",
            timeframe="5m",
            status="OPEN",
            open_time="2026-04-19T10:00:00+00:00",
            entry_price=100.0,
            qty=1.0,
            strategy_tag="baseline",
        ),
    )
    append_trade(
        csv_path,
        TradeRecord(
            trade_id="A-2",
            symbol="ETHUSDT",
            side="SHORT",
            timeframe="5m",
            status="CLOSED",
            open_time="2026-04-19T10:05:00+00:00",
            close_time="2026-04-19T10:10:00+00:00",
            net_pnl=5.0,
            strategy_tag="baseline",
            exit_reason="TAKE_PROFIT",
        ),
    )
    update_trade(
        csv_path,
        "A-1",
        {
            "status": "CLOSED",
            "close_time": "2026-04-19T10:15:00+00:00",
            "net_pnl": -1.5,
            "pnl": -1.5,
            "exit_reason": "STOP_LOSS",
        },
    )

    view = dashboard.TradeDashboard(str(csv_path))
    view.run()
    output = capsys.readouterr().out

    assert "=== Global Performance ===" in output
    assert "Net PnL" in output
    assert "3.5000 USDT" in output
