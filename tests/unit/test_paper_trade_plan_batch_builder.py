"""Unit test: trade plan batch builder."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.trade_plan_batch_builder import build_trade_plans


def _make_signal(symbol="BTCUSDT", price=104500.0) -> dict:
    return {"symbol": symbol, "interval": "5m", "time": "2026-06-14 10:00:00",
            "price": price, "signal_level": "B", "drop_pct": 3.5,
            "ma25": price * 0.99, "ma99": price * 0.98,
            "volume_ratio": 1.5, "above_ma99": True, "reason": "test"}


def test_batch_build_basic() -> None:
    signals = [_make_signal()]
    batch = build_trade_plans(signals)
    assert batch.plans_created == 1


def test_batch_build_multiple() -> None:
    signals = [_make_signal("BTCUSDT"), _make_signal("ETHUSDT", 2650.0)]
    batch = build_trade_plans(signals)
    assert batch.plans_created == 2


def test_batch_rejects_invalid() -> None:
    signals = [{"symbol": "", "price": 0}]
    batch = build_trade_plans(signals)
    assert batch.plans_created == 0


def test_batch_dry_run_only() -> None:
    signals = [_make_signal()]
    batch = build_trade_plans(signals)
    for p in batch.plans:
        assert p["dry_run_only"] is True


def test_batch_verdict() -> None:
    batch = build_trade_plans([])
    assert "TRADE_PLAN_BATCH_READY" in batch.final_verdict


def main() -> None:
    test_batch_build_basic()
    test_batch_build_multiple()
    test_batch_rejects_invalid()
    test_batch_dry_run_only()
    test_batch_verdict()
    print("test_paper_trade_plan_batch_builder: ALL PASS")


if __name__ == "__main__":
    main()
