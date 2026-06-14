"""Unit test: paper trading ops models."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.models import (
    new_id, utc_now_iso, LogFreshnessReport, PaperStateAudit,
    StrategyQualityMetrics, SignalQualityDashboard, DailyOpsBundle,
    ScheduledRunPlan, OpsAlertPayload,
)


def test_new_id_prefix() -> None:
    assert new_id("T").startswith("T_")
    assert len(new_id("T")) == 14


def test_utc_now_iso_format() -> None:
    ts = utc_now_iso()
    assert "T" in ts
    assert "+" in ts or "Z" in ts


def test_log_freshness_report_to_dict() -> None:
    r = LogFreshnessReport(
        report_id="LFR_test", created_at="2026-01-01T00:00:00+00:00",
        scanner_path="/tmp", signals_file_exists=True, alerts_file_exists=True,
        scan_detail_file_exists=True, errors_file_exists=False,
        latest_signal_time="2026-01-01 00:00:00", latest_alert_time=None,
        latest_scan_detail_time=None, minutes_since_latest_signal=1.0,
        minutes_since_latest_alert=None, minutes_since_latest_scan_detail=None,
        freshness_status="FRESH", stale_reasons=[], final_verdict="OK",
    )
    d = r.to_dict()
    assert d["report_id"] == "LFR_test"
    assert d["freshness_status"] == "FRESH"


def test_paper_state_audit_to_dict() -> None:
    a = PaperStateAudit(
        audit_id="PSA_test", created_at="2026-01-01T00:00:00+00:00",
        store_path="/tmp/x.jsonl", records_total=5,
        duplicate_plan_ids=0, duplicate_position_ids=0,
        invalid_status_count=0, not_dry_run_count=0,
        stale_open_count=0, stale_planned_count=0,
        missing_price_field_count=0, audit_status="PASS",
        audit_notes=["ok"], final_verdict="OK",
    )
    assert a.to_dict()["audit_status"] == "PASS"


def test_strategy_quality_metrics_to_dict() -> None:
    m = StrategyQualityMetrics(
        metrics_id="SQM_test", created_at="2026-01-01T00:00:00+00:00",
        total_positions=5, closed_positions=4, open_positions=1,
        tp1_count=1, tp2_count=1, tp3_count=1, stop_count=1,
        time_stop_count=0, win_count=3, loss_count=1,
        win_rate=75.0, avg_pnl_r=1.5, median_pnl_r=1.5,
        expectancy_r=1.0, best_pnl_r=4.0, worst_pnl_r=-1.0,
        profit_factor_placeholder=3.0, avg_bars_held=10.0,
        max_bars_held=30, symbol_breakdown={},
        sample_status="INSUFFICIENT_SAMPLE", final_verdict="OK",
    )
    assert m.to_dict()["win_rate"] == 75.0


def test_signal_quality_dashboard_to_dict() -> None:
    d = SignalQualityDashboard(
        dashboard_id="SQD_test", created_at="2026-01-01T00:00:00+00:00",
        period="all_time", raw_signals=10, deduped_signals=8,
        plans_created=6, plans_rejected=2, paper_positions_total=5,
        open_positions=1, closed_positions=4, tp_hit_count=3,
        stop_count=1, top_symbols_by_signal=[], top_symbols_by_tp=[],
        top_symbols_by_stop=[], best_symbols=[], worst_symbols=[],
        quality_grade="B", quality_notes=["ok"], final_verdict="OK",
    )
    assert d.to_dict()["quality_grade"] == "B"


def test_daily_ops_bundle_to_dict() -> None:
    b = DailyOpsBundle(
        bundle_id="DOB_test", created_at="2026-01-01T00:00:00+00:00",
        date="2026-01-01", freshness_status="FRESH",
        paper_state_status="PASS", strategy_sample_status="PROMISING",
        dashboard_grade="A", critical_alerts=[], warnings=[],
        recommended_actions=["monitor"], operator_checklist=["check"],
        final_verdict="OK",
    )
    assert b.to_dict()["date"] == "2026-01-01"


def test_scheduled_run_plan_to_dict() -> None:
    p = ScheduledRunPlan(
        plan_id="SRP_test", created_at="2026-01-01T00:00:00+00:00",
        tasks=({"interval": "*/5", "description": "test"},),
        cron_template="*/5 * * * *", systemd_template="[Unit]\nTest",
        final_verdict="OK",
    )
    d = p.to_dict()
    assert len(d["tasks"]) == 1
    assert "systemd_template" in d


def test_ops_alert_payload_to_dict() -> None:
    p = OpsAlertPayload(
        payload_id="OAP_test", created_at="2026-01-01T00:00:00+00:00",
        title="[DRY-RUN] Test", date="2026-01-01",
        freshness_status="FRESH", paper_state_status="PASS",
        strategy_sample_status="PROMISING", dashboard_grade="A",
        critical_alerts=[], warnings=[], recommended_actions=[],
        dry_run_only=True, final_verdict="OK",
    )
    assert p.to_dict()["dry_run_only"] is True


def main() -> None:
    test_new_id_prefix()
    test_utc_now_iso_format()
    test_log_freshness_report_to_dict()
    test_paper_state_audit_to_dict()
    test_strategy_quality_metrics_to_dict()
    test_signal_quality_dashboard_to_dict()
    test_daily_ops_bundle_to_dict()
    test_scheduled_run_plan_to_dict()
    test_ops_alert_payload_to_dict()
    print("test_paper_ops_models: ALL PASS")


if __name__ == "__main__":
    main()
