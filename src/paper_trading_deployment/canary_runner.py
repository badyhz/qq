"""Canary runner — validates key runners execute without errors."""
from __future__ import annotations
import pathlib, sys
from src.paper_trading_deployment.models import CanaryRunReport, new_id, utc_now_iso

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def _try_run(name: str, func) -> tuple[bool, str]:
    try:
        func()
        return True, ""
    except Exception as e:
        return False, str(e)


def run_canary(repo_path: str | None = None) -> CanaryRunReport:
    steps: list[tuple[str, bool, str]] = []

    # 1. Server config check
    def step_config():
        from src.paper_trading_deployment.server_config import build_server_config
        cfg = build_server_config()
        assert cfg.deployment_name

    steps.append(("server_config_check", *_try_run("config", step_config)))

    # 2. Deployment preflight
    def step_preflight():
        from src.paper_trading_deployment.preflight_check import run_preflight
        r = run_preflight(str(ROOT), "")
        assert r.preflight_status in ("PASS", "FAIL")

    steps.append(("deployment_preflight", *_try_run("preflight", step_preflight)))

    # 3. Log source check
    def step_log_source():
        from src.paper_trading_ops.log_freshness_monitor import check_freshness
        r = check_freshness(str(ROOT / "tests" / "fixtures" / "paper_trading_ops" / "scanner"))
        assert r.freshness_status

    steps.append(("log_source_check", *_try_run("log_source", step_log_source)))

    # 4. State audit
    def step_state_audit():
        from src.paper_trading_ops.paper_state_auditor import audit_store
        fixture = ROOT / "tests" / "fixtures" / "paper_trading_ops" / "paper_positions.jsonl"
        if fixture.exists():
            r = audit_store(fixture)
            assert r.audit_status

    steps.append(("state_audit", *_try_run("audit", step_state_audit)))

    # 5. Strategy metrics
    def step_metrics():
        from src.paper_trading_ops.strategy_quality_metrics import compute_metrics
        import json
        fixture = ROOT / "tests" / "fixtures" / "paper_trading_ops" / "paper_positions.jsonl"
        if fixture.exists():
            positions = [json.loads(l) for l in fixture.read_text().splitlines() if l.strip()]
            r = compute_metrics(positions)
            assert r.sample_status

    steps.append(("strategy_metrics", *_try_run("metrics", step_metrics)))

    # 6. Signal dashboard
    def step_dashboard():
        from src.paper_trading_ops.signal_quality_dashboard import build_dashboard
        r = build_dashboard(0, 0, 0, 0, [])
        assert r.quality_grade

    steps.append(("signal_dashboard", *_try_run("dashboard", step_dashboard)))

    # 7. Daily bundle
    def step_bundle():
        from src.paper_trading_ops.models import (
            LogFreshnessReport, PaperStateAudit, StrategyQualityMetrics,
            SignalQualityDashboard, new_id as nid, utc_now_iso as now,
        )
        from src.paper_trading_ops.daily_ops_bundle import build_ops_bundle
        f = LogFreshnessReport(report_id=nid("L"), created_at=now(), scanner_path="",
            signals_file_exists=True, alerts_file_exists=True,
            scan_detail_file_exists=True, errors_file_exists=False,
            latest_signal_time=None, latest_alert_time=None, latest_scan_detail_time=None,
            minutes_since_latest_signal=None, minutes_since_latest_alert=None,
            minutes_since_latest_scan_detail=None,
            freshness_status="NO_DATA", stale_reasons=[], final_verdict="OK")
        a = PaperStateAudit(audit_id=nid("P"), created_at=now(), store_path="",
            records_total=0, duplicate_plan_ids=0, duplicate_position_ids=0,
            invalid_status_count=0, not_dry_run_count=0,
            stale_open_count=0, stale_planned_count=0,
            missing_price_field_count=0, audit_status="PASS",
            audit_notes=[], final_verdict="OK")
        m = StrategyQualityMetrics(metrics_id=nid("S"), created_at=now(),
            total_positions=0, closed_positions=0, open_positions=0,
            tp1_count=0, tp2_count=0, tp3_count=0, stop_count=0,
            time_stop_count=0, win_count=0, loss_count=0,
            win_rate=0.0, avg_pnl_r=0.0, median_pnl_r=0.0,
            expectancy_r=0.0, best_pnl_r=0.0, worst_pnl_r=0.0,
            profit_factor_placeholder=0.0, avg_bars_held=0.0,
            max_bars_held=0, symbol_breakdown={},
            sample_status="INSUFFICIENT_SAMPLE", final_verdict="OK")
        d = SignalQualityDashboard(dashboard_id=nid("D"), created_at=now(),
            period="all_time", raw_signals=0, deduped_signals=0,
            plans_created=0, plans_rejected=0, paper_positions_total=0,
            open_positions=0, closed_positions=0, tp_hit_count=0,
            stop_count=0, top_symbols_by_signal=[], top_symbols_by_tp=[],
            top_symbols_by_stop=[], best_symbols=[], worst_symbols=[],
            quality_grade="INSUFFICIENT_DATA", quality_notes=[],
            final_verdict="OK")
        bundle = build_ops_bundle(f, a, m, d)
        assert bundle.final_verdict

    steps.append(("daily_bundle", *_try_run("bundle", step_bundle)))

    # 8. Alert payload
    def step_alert():
        from src.paper_trading_ops.ops_alert_payload import generate_alert_payload
        # Reuse bundle from step 7
        step_bundle()
        from src.paper_trading_ops.models import (
            LogFreshnessReport, PaperStateAudit, StrategyQualityMetrics,
            SignalQualityDashboard, new_id as nid, utc_now_iso as now,
        )
        from src.paper_trading_ops.daily_ops_bundle import build_ops_bundle
        f = LogFreshnessReport(report_id=nid("L"), created_at=now(), scanner_path="",
            signals_file_exists=True, alerts_file_exists=True,
            scan_detail_file_exists=True, errors_file_exists=False,
            latest_signal_time=None, latest_alert_time=None, latest_scan_detail_time=None,
            minutes_since_latest_signal=None, minutes_since_latest_alert=None,
            minutes_since_latest_scan_detail=None,
            freshness_status="NO_DATA", stale_reasons=[], final_verdict="OK")
        a = PaperStateAudit(audit_id=nid("P"), created_at=now(), store_path="",
            records_total=0, duplicate_plan_ids=0, duplicate_position_ids=0,
            invalid_status_count=0, not_dry_run_count=0,
            stale_open_count=0, stale_planned_count=0,
            missing_price_field_count=0, audit_status="PASS",
            audit_notes=[], final_verdict="OK")
        m = StrategyQualityMetrics(metrics_id=nid("S"), created_at=now(),
            total_positions=0, closed_positions=0, open_positions=0,
            tp1_count=0, tp2_count=0, tp3_count=0, stop_count=0,
            time_stop_count=0, win_count=0, loss_count=0,
            win_rate=0.0, avg_pnl_r=0.0, median_pnl_r=0.0,
            expectancy_r=0.0, best_pnl_r=0.0, worst_pnl_r=0.0,
            profit_factor_placeholder=0.0, avg_bars_held=0.0,
            max_bars_held=0, symbol_breakdown={},
            sample_status="INSUFFICIENT_SAMPLE", final_verdict="OK")
        d = SignalQualityDashboard(dashboard_id=nid("D"), created_at=now(),
            period="all_time", raw_signals=0, deduped_signals=0,
            plans_created=0, plans_rejected=0, paper_positions_total=0,
            open_positions=0, closed_positions=0, tp_hit_count=0,
            stop_count=0, top_symbols_by_signal=[], top_symbols_by_tp=[],
            top_symbols_by_stop=[], best_symbols=[], worst_symbols=[],
            quality_grade="INSUFFICIENT_DATA", quality_notes=[],
            final_verdict="OK")
        bundle = build_ops_bundle(f, a, m, d)
        payload = generate_alert_payload(bundle)
        assert payload.dry_run_only is True

    steps.append(("alert_payload", *_try_run("alert", step_alert)))

    # 9. Deployment safety regression
    def step_safety():
        from src.paper_trading_deployment.deployment_safety_regression import run_safety_regression
        r = run_safety_regression()
        assert r.total_flagged == 0

    steps.append(("deployment_safety", *_try_run("safety", step_safety)))

    passed = sum(1 for _, ok, _ in steps if ok)
    failed_list = [name for name, ok, _ in steps if not ok]
    total = len(steps)
    status = "PASS" if not failed_list else "FAIL"

    return CanaryRunReport(
        canary_id=new_id("CNR"), created_at=utc_now_iso(),
        steps_total=total, steps_passed=passed, steps_failed=len(failed_list),
        failed_steps=failed_list, canary_status=status,
        final_verdict=f"PAPER_OPS_CANARY_DRY_RUN_READY|STATUS={status}|PASSED={passed}|FAILED={len(failed_list)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
