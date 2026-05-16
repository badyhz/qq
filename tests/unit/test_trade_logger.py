import csv
from pathlib import Path

import pytest

from core.trade_logger import (
    TRADE_CSV_COLUMNS,
    TradeLogger,
    TradeRecord,
    append_trade,
    compute_trade_economics,
    ensure_csv_schema,
    update_trade,
)


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    return tmp_path / "trades.csv"


def read_rows(csv_path: Path) -> list[dict]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_ensure_csv_schema_creates_header(csv_path: Path):
    ensure_csv_schema(csv_path)

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)

    assert header == TRADE_CSV_COLUMNS


def test_append_trade_writes_row(csv_path: Path):
    row = append_trade(
        csv_path,
        TradeRecord(
            trade_id="T-1",
            symbol="BTCUSDT",
            side="SHORT",
            timeframe="5m",
            status="OPEN",
            open_time="2026-04-19T12:00:00+00:00",
            entry_price=100.0,
            qty=2.5,
            leverage=2.0,
        ),
    )

    rows = read_rows(csv_path)

    assert row["trade_id"] == "T-1"
    assert len(rows) == 1
    assert rows[0]["trade_id"] == "T-1"
    assert rows[0]["status"] == "OPEN"
    assert float(rows[0]["entry_price"]) == pytest.approx(100.0)
    assert float(rows[0]["qty"]) == pytest.approx(2.5)


def test_update_trade_updates_existing_row(csv_path: Path):
    append_trade(
        csv_path,
        TradeRecord(
            trade_id="T-2",
            symbol="ETHUSDT",
            side="LONG",
            timeframe="15m",
            status="OPEN",
            open_time="2026-04-19T12:00:00+00:00",
            entry_price=2000.0,
            qty=1.0,
        ),
    )

    updated = update_trade(
        csv_path,
        "T-2",
        {
            "status": "CLOSED",
            "close_time": "2026-04-19T12:15:00+00:00",
            "exit_price": 2050.0,
            "net_pnl": 45.0,
        },
    )

    rows = read_rows(csv_path)

    assert updated is True
    assert rows[0]["status"] == "CLOSED"
    assert rows[0]["close_time"] == "2026-04-19T12:15:00+00:00"
    assert float(rows[0]["exit_price"]) == pytest.approx(2050.0)
    assert float(rows[0]["net_pnl"]) == pytest.approx(45.0)


def test_compute_trade_economics_for_long():
    economics = compute_trade_economics(
        side="LONG",
        entry_price=100.0,
        exit_price=110.0,
        qty=2.0,
        risk_amount=10.0,
        fee_open=0.5,
        fee_close=0.5,
        slippage_open=0.2,
        slippage_close=0.2,
        funding_fee=0.1,
        equity_before=1000.0,
    )

    assert economics["notional"] == pytest.approx(200.0)
    assert economics["gross_pnl"] == pytest.approx(20.0)
    assert economics["fees_total"] == pytest.approx(1.0)
    assert economics["slippage_total"] == pytest.approx(0.4)
    assert economics["total_cost"] == pytest.approx(1.1)
    assert economics["net_pnl"] == pytest.approx(18.9)
    assert economics["pnl_pct"] == pytest.approx(9.45)
    assert economics["r_multiple"] == pytest.approx(1.89)
    assert economics["equity_after"] == pytest.approx(1018.9)
    assert economics["return_on_equity"] == pytest.approx(1.89)


def test_compute_trade_economics_for_short():
    economics = compute_trade_economics(
        side="SHORT",
        entry_price=100.0,
        exit_price=90.0,
        qty=2.0,
        risk_amount=8.0,
        fee_open=0.5,
        fee_close=0.5,
        borrow_cost=0.25,
        other_cost=0.25,
        equity_before=500.0,
    )

    assert economics["notional"] == pytest.approx(200.0)
    assert economics["gross_pnl"] == pytest.approx(20.0)
    assert economics["fees_total"] == pytest.approx(1.0)
    assert economics["slippage_total"] == pytest.approx(0.0)
    assert economics["total_cost"] == pytest.approx(1.5)
    assert economics["net_pnl"] == pytest.approx(18.5)
    assert economics["pnl_pct"] == pytest.approx(9.25)
    assert economics["r_multiple"] == pytest.approx(2.3125)
    assert economics["equity_after"] == pytest.approx(518.5)
    assert economics["return_on_equity"] == pytest.approx(3.7)


def test_ensure_csv_schema_migrates_legacy_columns(csv_path: Path):
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["trade_id", "symbol", "side", "quantity", "pnl", "entry_time"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "trade_id": "legacy-1",
                "symbol": "SOLUSDT",
                "side": "SHORT",
                "quantity": "3",
                "pnl": "12.5",
                "entry_time": "2026-04-19T10:00:00+00:00",
            }
        )

    ensure_csv_schema(csv_path)
    rows = read_rows(csv_path)

    assert list(rows[0].keys()) == TRADE_CSV_COLUMNS
    assert rows[0]["trade_id"] == "legacy-1"
    assert rows[0]["symbol"] == "SOLUSDT"
    assert rows[0]["side"] == "SHORT"
    assert rows[0]["qty"] == "3"
    assert rows[0]["net_pnl"] == "12.5"
    assert rows[0]["open_time"] == "2026-04-19T10:00:00+00:00"


def test_trade_logger_log_trade_accepts_legacy_closed_trade(csv_path: Path):
    logger = TradeLogger(
        {
            "timeframe": "5m",
            "strategy_profile": "baseline",
            "risk": {"starting_balance_usdt": 1000.0, "leverage": 2},
            "paths": {"trades_csv": str(csv_path)},
        }
    )

    logger.log_trade(
        {
            "trade_id": 7,
            "symbol": "BTCUSDT",
            "side": "SHORT",
            "strategy_profile": "baseline",
            "entry_price": 100.0,
            "reference_entry_price": 100.0,
            "entry_fill_price": 99.9,
            "exit_price": 95.0,
            "reference_exit_price": 94.8,
            "exit_fill_price": 95.0,
            "quantity": 2.0,
            "entry_fee": 0.08,
            "exit_fee": 0.076,
            "gross_pnl": 9.8,
            "total_fees": 0.156,
            "net_pnl": 9.644,
            "estimated_loss_at_stop": 5.0,
            "entry_time": "2026-04-19T10:00:00+00:00",
            "exit_time": "2026-04-19T10:05:00+00:00",
            "duration_sec": 300,
            "exit_reason": "TAKE_PROFIT",
        }
    )

    rows = read_rows(csv_path)

    assert len(rows) == 1
    assert rows[0]["trade_id"] == "7"
    assert rows[0]["status"] == "CLOSED"
    assert rows[0]["timeframe"] == "5m"
    assert rows[0]["strategy_tag"] == "baseline"
    assert rows[0]["holding_seconds"] == "300"
    assert rows[0]["holding_bars"] == "1"
    assert float(rows[0]["fee_open"]) == pytest.approx(0.08)
    assert float(rows[0]["fee_close"]) == pytest.approx(0.076)
    assert float(rows[0]["fees_total"]) == pytest.approx(0.156)
    assert float(rows[0]["risk_amount"]) == pytest.approx(5.0)
    assert float(rows[0]["r_multiple"]) == pytest.approx(9.644 / 5.0)
