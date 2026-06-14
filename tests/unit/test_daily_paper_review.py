"""Unit test: daily paper review."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.daily_paper_review import generate_daily_review
from src.paper_trading_pipeline.models import (
    ScannerLogSnapshot, DedupedSignalBatch, TradePlanBatch, PaperPositionRecord)


def _make_snapshot(signals=3) -> ScannerLogSnapshot:
    return ScannerLogSnapshot(
        snapshot_id="S1", scanner_path="/tmp", signals_count=signals,
        alerts_count=2, scan_detail_count=10, errors_count=0,
        latest_signal_time=None, latest_alert_time=None,
        source_files={}, source_status="ALL_SOURCES_PRESENT", final_verdict="TEST")


def _make_deduped(raw=3, deduped=3) -> DedupedSignalBatch:
    return DedupedSignalBatch(
        batch_id="D1", created_at="", raw_count=raw, deduped_count=deduped,
        duplicate_count=0, cooldown_filtered_count=0, force_alert_count=0,
        signals=(), dedup_notes=[], final_verdict="TEST")


def _make_batch(created=3, rejected=0) -> TradePlanBatch:
    return TradePlanBatch(
        batch_id="B1", created_at="", source_snapshot_id="S1",
        total_signals=created, plans_created=created, plans_rejected=rejected,
        plans=(), rejection_reasons=[], final_verdict="TEST")


def _make_position(status="PAPER_OPEN") -> PaperPositionRecord:
    return PaperPositionRecord(
        record_id="R1", paper_position_id="PP1", plan_id="TP1",
        symbol="BTCUSDT", timeframe="5m", status=status,
        entry_price=104500.0, stop_loss=101400.0,
        take_profit_1=109150.0, take_profit_2=112150.0, take_profit_3=116800.0,
        created_at="", updated_at="", source_signal_id="SIG1", dry_run_only=True)


def test_review_basic() -> None:
    review = generate_daily_review(
        _make_snapshot(), _make_deduped(), _make_batch(), [])
    assert review.raw_signals == 3
    assert review.trade_plans_created == 3


def test_review_with_positions() -> None:
    positions = [_make_position("PAPER_OPEN"), _make_position("PAPER_STOPPED")]
    review = generate_daily_review(
        _make_snapshot(), _make_deduped(), _make_batch(), positions)
    assert review.paper_positions_total == 2
    assert review.paper_open_count == 1
    assert review.stop_count == 1


def test_review_verdict() -> None:
    review = generate_daily_review(
        _make_snapshot(), _make_deduped(), _make_batch(), [])
    assert "DAILY_PAPER_TRADING_REVIEW_READY" in review.final_verdict


def test_review_top_symbols() -> None:
    positions = [_make_position(), _make_position()]
    review = generate_daily_review(
        _make_snapshot(), _make_deduped(), _make_batch(), positions)
    assert "BTCUSDT" in review.top_symbols


def test_review_risk_notes() -> None:
    batch = _make_batch(rejected=2)
    review = generate_daily_review(
        _make_snapshot(), _make_deduped(), batch, [])
    assert len(review.risk_notes) > 0


def main() -> None:
    test_review_basic()
    test_review_with_positions()
    test_review_verdict()
    test_review_top_symbols()
    test_review_risk_notes()
    print("test_daily_paper_review: ALL PASS")


if __name__ == "__main__":
    main()
