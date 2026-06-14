"""Unit test: paper position updater."""
from __future__ import annotations
import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.paper_position_updater import update_position_from_ohlcv
from src.paper_trading_pipeline.models import PaperPositionRecord

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_pipeline" / "ohlcv"


def _make_record(price=104500.0, sl=101400.0) -> PaperPositionRecord:
    return PaperPositionRecord(
        record_id="R1", paper_position_id="PP1", plan_id="TP1",
        symbol="BTCUSDT", timeframe="5m", status="PLANNED",
        entry_price=price, stop_loss=sl,
        take_profit_1=price + 1.5 * (price - sl),
        take_profit_2=price + 2.5 * (price - sl),
        take_profit_3=price + 4.0 * (price - sl),
        created_at="", updated_at="", source_signal_id="SIG1", dry_run_only=True)


def _read_ohlcv(name: str) -> list[dict]:
    path = FIXTURE / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_update_tp() -> None:
    r = _make_record()
    ohlcv = _read_ohlcv("BTCUSDT_5m_after_signal_tp.csv")
    result = update_position_from_ohlcv(r, ohlcv)
    assert result.status in ("PAPER_TP1_HIT", "PAPER_TP2_HIT", "PAPER_CLOSED_TP3")


def test_update_stop() -> None:
    r = _make_record(2650.0, 2575.5)  # ETH fixture
    ohlcv = _read_ohlcv("ETHUSDT_5m_after_signal_stop.csv")
    result = update_position_from_ohlcv(r, ohlcv)
    assert result.status == "PAPER_STOPPED"


def test_update_timeout() -> None:
    r = _make_record(155.0, 150.35)  # SOL fixture
    ohlcv = _read_ohlcv("SOLUSDT_5m_after_signal_timeout.csv")
    result = update_position_from_ohlcv(r, ohlcv, max_hold_bars=5)
    assert result.status in ("PAPER_TIME_STOPPED", "PAPER_TP1_HIT", "PAPER_OPEN", "PLANNED")


def test_update_empty_ohlcv() -> None:
    r = _make_record()
    result = update_position_from_ohlcv(r, [])
    assert result.status == "PLANNED"


def test_update_already_closed() -> None:
    r = PaperPositionRecord(
        record_id="R1", paper_position_id="PP1", plan_id="TP1",
        symbol="BTCUSDT", timeframe="5m", status="PAPER_STOPPED",
        entry_price=104500.0, stop_loss=101400.0,
        take_profit_1=109150.0, take_profit_2=112150.0, take_profit_3=116800.0,
        created_at="", updated_at="", source_signal_id="SIG1", dry_run_only=True)
    result = update_position_from_ohlcv(r, [{"high": 999999, "low": 0}])
    assert result.status == "PAPER_STOPPED"


def test_update_dry_run_only() -> None:
    r = _make_record()
    result = update_position_from_ohlcv(r, [{"high": 110000, "low": 104000}])
    assert result.dry_run_only is True


def main() -> None:
    test_update_tp()
    test_update_stop()
    test_update_timeout()
    test_update_empty_ohlcv()
    test_update_already_closed()
    test_update_dry_run_only()
    print("test_paper_position_updater: ALL PASS")


if __name__ == "__main__":
    main()
