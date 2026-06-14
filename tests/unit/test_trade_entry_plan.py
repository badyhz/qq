"""Unit test: entry plan."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.entry_plan import generate_entry_plan
from src.trade_plan_engine.models import SignalCandidate


def _make_signal(price=104500.0, level="B", above_ma99=True, vol_ratio=1.5, drop=3.5) -> SignalCandidate:
    return SignalCandidate(
        signal_id="SIG_test", symbol="BTCUSDT", timeframe="5m",
        signal_time="2026-06-12T16:45:00", price=price, signal_level=level,
        drop_pct=drop, macd_dif=1.2e-05, macd_dea=1.1e-05, macd_hist=1.0e-06,
        ma7=104200.0, ma25=103800.0, ma99=103000.0, volume=5200.0,
        volume_ma5=3500.0, volume_ratio=vol_ratio, above_ma99=above_ma99,
        reason="test", source="macd_rebound_scanner")


def test_entry_type_breakout() -> None:
    sig = _make_signal(above_ma99=True, level="B")
    entry = generate_entry_plan(sig)
    assert entry["entry_type"] == "BREAKOUT_OR_PULLBACK"


def test_entry_type_pullback() -> None:
    sig = _make_signal(above_ma99=False, level="B")
    entry = generate_entry_plan(sig)
    assert entry["entry_type"] == "PULLBACK"


def test_entry_zone_range() -> None:
    sig = _make_signal(price=1000.0)
    entry = generate_entry_plan(sig)
    assert entry["entry_zone_low"] < entry["entry_price"]
    assert entry["entry_zone_high"] > entry["entry_price"]
    assert entry["entry_zone_low"] == 995.0
    assert entry["entry_zone_high"] == 1005.0


def test_entry_confidence_high_volume() -> None:
    sig = _make_signal(vol_ratio=2.0, drop=5.0)
    entry = generate_entry_plan(sig)
    assert entry["confidence"] == "HIGH"


def test_entry_confidence_low() -> None:
    sig = _make_signal(vol_ratio=0.8, drop=1.0)
    entry = generate_entry_plan(sig)
    assert entry["confidence"] == "LOW"


def test_entry_reason_present() -> None:
    sig = _make_signal()
    entry = generate_entry_plan(sig)
    assert len(entry["entry_reason"]) > 0


def main() -> None:
    test_entry_type_breakout()
    test_entry_type_pullback()
    test_entry_zone_range()
    test_entry_confidence_high_volume()
    test_entry_confidence_low()
    test_entry_reason_present()
    print("test_trade_entry_plan: ALL PASS")


if __name__ == "__main__":
    main()
