"""Unit test: signal adapter."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.signal_adapter import adapt_signals

FIXTURE = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "trade_plan_engine")


def test_adapt_signals_count() -> None:
    result = adapt_signals(FIXTURE)
    assert result.total_valid == 3, f"Expected 3 valid, got {result.total_valid}"


def test_adapt_signals_dedup() -> None:
    result = adapt_signals(FIXTURE)
    assert result.total_deduplicated <= result.total_raw


def test_adapt_signals_fields() -> None:
    result = adapt_signals(FIXTURE)
    for c in result.candidates:
        assert c.price > 0
        assert c.symbol
        assert c.source in ("macd_rebound_scanner", "macd_rebound_scanner_alert")


def test_adapt_signals_verdict() -> None:
    result = adapt_signals(FIXTURE)
    assert "SIGNAL_ADAPTER_READY" in result.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in result.final_verdict


def test_adapt_empty_path() -> None:
    result = adapt_signals("/nonexistent/path")
    assert result.total_valid == 0


def main() -> None:
    test_adapt_signals_count()
    test_adapt_signals_dedup()
    test_adapt_signals_fields()
    test_adapt_signals_verdict()
    test_adapt_empty_path()
    print("test_trade_plan_signal_adapter: ALL PASS")


if __name__ == "__main__":
    main()
