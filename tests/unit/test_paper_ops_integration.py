"""Integration test: paper ops full pipeline."""
from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.log_freshness_monitor import check_freshness
from src.paper_trading_ops.paper_state_auditor import audit_store
from src.paper_trading_ops.strategy_quality_metrics import compute_metrics
from src.paper_trading_ops.signal_quality_dashboard import build_dashboard
from src.paper_trading_ops.daily_ops_bundle import build_ops_bundle
from src.paper_trading_ops.ops_alert_payload import generate_alert_payload
from src.paper_trading_ops.scheduled_run_plan import create_scheduled_plan
from src.paper_trading_ops.ops_safety_regression import run_safety_regression

FIXTURE_SCANNER = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_ops" / "scanner"
FIXTURE_STORE = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_ops" / "paper_positions.jsonl"


def _load_positions() -> list[dict]:
    positions = []
    for line in FIXTURE_STORE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            positions.append(json.loads(line))
    return positions


def test_full_pipeline() -> None:
    # Freshness
    freshness = check_freshness(str(FIXTURE_SCANNER))
    assert freshness.freshness_status in ("FRESH", "STALE_WARNING", "STALE_CRITICAL", "NO_DATA")

    # State audit
    audit = audit_store(FIXTURE_STORE)
    assert audit.audit_status in ("PASS", "WARNING", "FAIL")

    # Metrics
    positions = _load_positions()
    metrics = compute_metrics(positions)
    assert metrics.total_positions == 5

    # Dashboard
    dashboard = build_dashboard(10, 8, 6, 2, positions,
                                expectancy_r=metrics.expectancy_r, win_rate=metrics.win_rate)
    assert dashboard.quality_grade in ("A", "B", "C", "D", "INSUFFICIENT_DATA")

    # Bundle
    bundle = build_ops_bundle(freshness, audit, metrics, dashboard)
    assert "DAILY_PAPER_OPS_BUNDLE_READY" in bundle.final_verdict

    # Alert payload
    payload = generate_alert_payload(bundle)
    assert payload.dry_run_only is True
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in payload.final_verdict

    # Scheduled plan
    plan = create_scheduled_plan()
    assert "NOT_INSTALLED" in plan.final_verdict

    # Safety regression
    safety = run_safety_regression()
    assert safety.total_flagged == 0


def test_pipeline_verdicts_contain_safety() -> None:
    freshness = check_freshness(str(FIXTURE_SCANNER))
    audit = audit_store(FIXTURE_STORE)
    positions = _load_positions()
    metrics = compute_metrics(positions)
    dashboard = build_dashboard(10, 8, 6, 2, positions)
    bundle = build_ops_bundle(freshness, audit, metrics, dashboard)
    payload = generate_alert_payload(bundle)

    for verdict in [freshness.final_verdict, audit.final_verdict, metrics.final_verdict,
                    dashboard.final_verdict, bundle.final_verdict, payload.final_verdict]:
        assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in verdict, f"Missing safety in: {verdict}"


def main() -> None:
    test_full_pipeline()
    test_pipeline_verdicts_contain_safety()
    print("test_paper_ops_integration: ALL PASS")


if __name__ == "__main__":
    main()
