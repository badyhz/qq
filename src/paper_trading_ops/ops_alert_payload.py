"""Ops alert payload — dry-run only, no real send."""
from __future__ import annotations
from src.paper_trading_ops.models import DailyOpsBundle, OpsAlertPayload, new_id, utc_now_iso


def generate_alert_payload(bundle: DailyOpsBundle) -> OpsAlertPayload:
    return OpsAlertPayload(
        payload_id=new_id("OAP"), created_at=utc_now_iso(),
        title=f"[DRY-RUN] Paper Trading Ops Alert {bundle.date}",
        date=bundle.date,
        freshness_status=bundle.freshness_status,
        paper_state_status=bundle.paper_state_status,
        strategy_sample_status=bundle.strategy_sample_status,
        dashboard_grade=bundle.dashboard_grade,
        critical_alerts=bundle.critical_alerts,
        warnings=bundle.warnings,
        recommended_actions=bundle.recommended_actions,
        dry_run_only=True,
        final_verdict="PAPER_OPS_ALERT_PAYLOAD_DRY_RUN_READY|DRY_RUN_ONLY=TRUE|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
