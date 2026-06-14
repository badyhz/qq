"""Unit test: paper ops daily bundle."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.models import (
    LogFreshnessReport, PaperStateAudit, StrategyQualityMetrics,
    SignalQualityDashboard, new_id, utc_now_iso,
)
from src.paper_trading_ops.daily_ops_bundle import build_ops_bundle


def _make_freshness(status: str = "FRESH") -> LogFreshnessReport:
    return LogFreshnessReport(
        report_id=new_id("LFR"), created_at=utc_now_iso(), scanner_path="/tmp",
        signals_file_exists=True, alerts_file_exists=True,
        scan_detail_file_exists=True, errors_file_exists=False,
        latest_signal_time=None, latest_alert_time=None, latest_scan_detail_time=None,
        minutes_since_latest_signal=None, minutes_since_latest_alert=None,
        minutes_since_latest_scan_detail=None,
        freshness_status=status, stale_reasons=[], final_verdict="OK",
    )


def _make_audit(status: str = "PASS") -> PaperStateAudit:
    return PaperStateAudit(
        audit_id=new_id("PSA"), created_at=utc_now_iso(), store_path="/tmp",
        records_total=5, duplicate_plan_ids=0, duplicate_position_ids=0,
        invalid_status_count=0, not_dry_run_count=0,
        stale_open_count=0, stale_planned_count=0,
        missing_price_field_count=0, audit_status=status,
        audit_notes=[], final_verdict="OK",
    )


def _make_metrics(sample: str = "PROMISING", expectancy: float = 0.5, closed: int = 25) -> StrategyQualityMetrics:
    return StrategyQualityMetrics(
        metrics_id=new_id("SQM"), created_at=utc_now_iso(),
        total_positions=30, closed_positions=closed, open_positions=5,
        tp1_count=5, tp2_count=3, tp3_count=2, stop_count=5,
        time_stop_count=0, win_count=15, loss_count=5,
        win_rate=60.0, avg_pnl_r=1.0, median_pnl_r=1.0,
        expectancy_r=expectancy, best_pnl_r=4.0, worst_pnl_r=-1.0,
        profit_factor_placeholder=2.0, avg_bars_held=10.0,
        max_bars_held=30, symbol_breakdown={},
        sample_status=sample, final_verdict="OK",
    )


def _make_dashboard(grade: str = "B") -> SignalQualityDashboard:
    return SignalQualityDashboard(
        dashboard_id=new_id("SQD"), created_at=utc_now_iso(), period="all_time",
        raw_signals=10, deduped_signals=8, plans_created=6, plans_rejected=2,
        paper_positions_total=5, open_positions=1, closed_positions=4,
        tp_hit_count=3, stop_count=1, top_symbols_by_signal=[],
        top_symbols_by_tp=[], top_symbols_by_stop=[],
        best_symbols=[], worst_symbols=[],
        quality_grade=grade, quality_notes=[], final_verdict="OK",
    )


def test_bundle_healthy() -> None:
    b = build_ops_bundle(
        _make_freshness("FRESH"), _make_audit("PASS"),
        _make_metrics(), _make_dashboard("A"),
    )
    assert "PAPER_TRADING_OPS_HEALTHY" in b.final_verdict
    assert len(b.critical_alerts) == 0


def test_bundle_warning() -> None:
    b = build_ops_bundle(
        _make_freshness("STALE_WARNING"), _make_audit("PASS"),
        _make_metrics(), _make_dashboard("B"),
    )
    assert "PAPER_TRADING_OPS_WARNING" in b.final_verdict
    assert len(b.warnings) > 0


def test_bundle_critical() -> None:
    b = build_ops_bundle(
        _make_freshness("STALE_CRITICAL"), _make_audit("FAIL"),
        _make_metrics(), _make_dashboard("D"),
    )
    assert "PAPER_TRADING_OPS_CRITICAL" in b.final_verdict
    assert len(b.critical_alerts) > 0


def test_bundle_verdict_format() -> None:
    b = build_ops_bundle(
        _make_freshness(), _make_audit(), _make_metrics(), _make_dashboard(),
    )
    assert "DAILY_PAPER_OPS_BUNDLE_READY" in b.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in b.final_verdict


def test_bundle_to_dict() -> None:
    b = build_ops_bundle(
        _make_freshness(), _make_audit(), _make_metrics(), _make_dashboard(),
    )
    d = b.to_dict()
    assert "bundle_id" in d
    assert "operator_checklist" in d


def main() -> None:
    test_bundle_healthy()
    test_bundle_warning()
    test_bundle_critical()
    test_bundle_verdict_format()
    test_bundle_to_dict()
    print("test_paper_ops_daily_bundle: ALL PASS")


if __name__ == "__main__":
    main()
