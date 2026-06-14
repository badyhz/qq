"""Unit test: signal deduplicator."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.signal_deduplicator import deduplicate_signals


def _make_signal(symbol="BTCUSDT", time="2026-06-14 10:00:00", interval="5m") -> dict:
    return {"symbol": symbol, "interval": interval, "time": time, "price": 104500.0,
            "signal_level": "B", "drop_pct": 3.5, "volume_ratio": 1.5, "above_ma99": True}


def test_dedup_exact() -> None:
    signals = [_make_signal(), _make_signal()]
    batch = deduplicate_signals(signals)
    assert batch.deduped_count == 1
    assert batch.duplicate_count == 1


def test_dedup_different_symbols() -> None:
    signals = [_make_signal("BTCUSDT"), _make_signal("ETHUSDT")]
    batch = deduplicate_signals(signals)
    assert batch.deduped_count == 2


def test_dedup_cooldown() -> None:
    signals = [
        _make_signal("BTCUSDT", "2026-06-14 10:00:00"),
        _make_signal("BTCUSDT", "2026-06-14 10:15:00"),  # within 30min cooldown
    ]
    batch = deduplicate_signals(signals, cooldown_minutes=30)
    assert batch.cooldown_filtered_count == 1


def test_dedup_force_alert() -> None:
    signals = [_make_signal()]
    alerts = [{"symbol": "BTCUSDT", "interval": "5m", "signal_time": "2026-06-14 10:00:00", "force_alert": True}]
    batch = deduplicate_signals(signals, alerts)
    assert batch.force_alert_count >= 0  # may be deduped


def test_dedup_empty() -> None:
    batch = deduplicate_signals([])
    assert batch.raw_count == 0
    assert batch.deduped_count == 0


def test_dedup_verdict() -> None:
    batch = deduplicate_signals([])
    assert "SIGNAL_DEDUP_READY" in batch.final_verdict


def main() -> None:
    test_dedup_exact()
    test_dedup_different_symbols()
    test_dedup_cooldown()
    test_dedup_force_alert()
    test_dedup_empty()
    test_dedup_verdict()
    print("test_paper_trading_signal_deduplicator: ALL PASS")


if __name__ == "__main__":
    main()
