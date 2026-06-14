"""Unit test: paper trading pipeline models."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.models import (
    ScannerLogSnapshot, DedupedSignalBatch, TradePlanBatch,
    PaperPositionRecord, ReplaySchedule, DailyPaperReview,
    FeishuPaperReviewPayload, new_id, utc_now_iso)


def test_new_id() -> None:
    assert new_id("T").startswith("T_")
    assert len(new_id("T")) == 14  # T_ + 12 hex


def test_utc_now_iso() -> None:
    ts = utc_now_iso()
    assert "T" in ts


def test_scanner_log_snapshot() -> None:
    s = ScannerLogSnapshot(
        snapshot_id="S1", scanner_path="/tmp", signals_count=3,
        alerts_count=2, scan_detail_count=10, errors_count=0,
        latest_signal_time=None, latest_alert_time=None,
        source_files={"data/signals.csv": True}, source_status="ALL_SOURCES_PRESENT",
        final_verdict="TEST")
    d = s.to_dict()
    assert d["signals_count"] == 3


def test_paper_position_record() -> None:
    r = PaperPositionRecord(
        record_id="R1", paper_position_id="PP1", plan_id="TP1",
        symbol="BTCUSDT", timeframe="5m", status="PLANNED",
        entry_price=104500.0, stop_loss=101400.0,
        take_profit_1=109150.0, take_profit_2=112150.0, take_profit_3=116800.0,
        created_at="", updated_at="", source_signal_id="SIG1",
        dry_run_only=True)
    assert r.dry_run_only is True
    assert r.status == "PLANNED"


def test_feishu_payload() -> None:
    f = FeishuPaperReviewPayload(
        payload_id="F1", created_at="", title="test", date="2026-06-14",
        raw_signals=3, deduped_signals=3, trade_plans_created=3,
        paper_open_count=1, paper_closed_count=0, tp_hit_count=0,
        stop_count=0, top_symbols=[], risk_notes=[], next_actions=[],
        dry_run_only=True, final_verdict="TEST")
    assert f.dry_run_only is True


def main() -> None:
    test_new_id()
    test_utc_now_iso()
    test_scanner_log_snapshot()
    test_paper_position_record()
    test_feishu_payload()
    print("test_paper_trading_models: ALL PASS")


if __name__ == "__main__":
    main()
