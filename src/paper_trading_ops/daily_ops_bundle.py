"""Daily ops bundle — aggregates all ops reports."""
from __future__ import annotations
from datetime import datetime, timezone
from src.paper_trading_ops.models import (
    LogFreshnessReport, PaperStateAudit, StrategyQualityMetrics,
    SignalQualityDashboard, DailyOpsBundle, new_id, utc_now_iso,
)


def build_ops_bundle(
    freshness: LogFreshnessReport,
    state_audit: PaperStateAudit,
    metrics: StrategyQualityMetrics,
    dashboard: SignalQualityDashboard,
) -> DailyOpsBundle:
    critical: list[str] = []
    warnings: list[str] = []
    actions: list[str] = []

    # Freshness
    if freshness.freshness_status == "STALE_CRITICAL":
        critical.append(f"Scanner logs critically stale ({freshness.minutes_since_latest_scan_detail}min)")
    elif freshness.freshness_status == "STALE_WARNING":
        warnings.append(f"Scanner logs stale ({freshness.minutes_since_latest_scan_detail}min)")
    elif freshness.freshness_status == "NO_DATA":
        critical.append("No scanner data found")

    # State audit
    if state_audit.audit_status == "FAIL":
        critical.append(f"Paper state audit FAILED: {'; '.join(state_audit.audit_notes[:3])}")
    elif state_audit.audit_status == "WARNING":
        warnings.append(f"Paper state warnings: {'; '.join(state_audit.audit_notes[:3])}")

    # Strategy
    if metrics.sample_status == "WEAK":
        warnings.append(f"Strategy quality WEAK: expectancy={metrics.expectancy_r:.2f}R")
    elif metrics.sample_status == "PROMISING":
        actions.append(f"Strategy showing promise: expectancy={metrics.expectancy_r:.2f}R, win_rate={metrics.win_rate:.1f}%")

    # Dashboard
    if dashboard.quality_grade == "D":
        critical.append(f"Signal quality grade D — negative edge")
    elif dashboard.quality_grade == "C":
        warnings.append(f"Signal quality grade C — marginal edge")

    # Actions
    if metrics.closed_positions < 20:
        actions.append(f"Need {20 - metrics.closed_positions} more closed trades for quality assessment")
    if not actions:
        actions.append("Continue monitoring — no immediate action needed")

    # Checklist
    checklist = [
        "Verify scanner is running",
        "Check paper positions store for anomalies",
        "Review strategy quality metrics",
        "Check for stale logs",
        "Review daily paper trading review",
    ]

    # Overall verdict
    if critical:
        verdict = "PAPER_TRADING_OPS_CRITICAL"
    elif warnings:
        verdict = "PAPER_TRADING_OPS_WARNING"
    else:
        verdict = "PAPER_TRADING_OPS_HEALTHY"

    return DailyOpsBundle(
        bundle_id=new_id("DOB"), created_at=utc_now_iso(),
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        freshness_status=freshness.freshness_status,
        paper_state_status=state_audit.audit_status,
        strategy_sample_status=metrics.sample_status,
        dashboard_grade=dashboard.quality_grade,
        critical_alerts=critical, warnings=warnings,
        recommended_actions=actions, operator_checklist=checklist,
        final_verdict=f"DAILY_PAPER_OPS_BUNDLE_READY|{verdict}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
