"""MACD rebound scanner daily report."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from src.external_scanner_integrations.macd_rebound_log_ingest import ingest_logs
from src.external_scanner_integrations.macd_rebound_health import run_health_check


@dataclass(frozen=True)
class DailyReport:
    report_id: str
    created_at: str
    report_date: str
    scanner_status: str
    health_score: int
    total_signals: int
    total_alerts: int
    failed_alerts: int
    top_symbols: list[str]
    recent_signals: list[dict]
    recent_alerts: list[dict]
    anomaly_summary: list[str]
    suggested_actions: list[str]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"report_id": self.report_id, "created_at": self.created_at,
                "report_date": self.report_date, "scanner_status": self.scanner_status,
                "health_score": self.health_score, "total_signals": self.total_signals,
                "total_alerts": self.total_alerts, "failed_alerts": self.failed_alerts,
                "top_symbols": self.top_symbols, "recent_signals": self.recent_signals,
                "recent_alerts": self.recent_alerts, "anomaly_summary": self.anomaly_summary,
                "suggested_actions": self.suggested_actions, "final_verdict": self.final_verdict}


def generate_daily_report(scanner_path: str) -> DailyReport:
    health = run_health_check(scanner_path)
    logs = ingest_logs(scanner_path)
    anomalies: list[str] = []
    actions: list[str] = []
    if logs.error_count > 0:
        anomalies.append(f"errors.log has {logs.error_count} lines")
        actions.append("Review logs/errors.log for scanner issues")
    if logs.failed_alerts > 0:
        anomalies.append(f"{logs.failed_alerts} alerts failed to send")
        actions.append("Check Feishu webhook configuration")
    if logs.total_signals == 0:
        anomalies.append("No signals recorded")
        actions.append("Verify scanner is running and market data is accessible")
    if health.health_score < 80:
        anomalies.append(f"Health score is {health.health_score}%")
        actions.append("Review missing components in health report")
    if not anomalies:
        anomalies.append("No anomalies detected")
        actions.append("No action needed")
    scanner_status = "HEALTHY" if health.health_score >= 80 else "DEGRADED"
    return DailyReport(
        report_id=f"MRD_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        report_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        scanner_status=scanner_status,
        health_score=health.health_score,
        total_signals=logs.total_signals,
        total_alerts=logs.total_alerts,
        failed_alerts=logs.failed_alerts,
        top_symbols=logs.top_symbols,
        recent_signals=[],
        recent_alerts=[],
        anomaly_summary=anomalies,
        suggested_actions=actions,
        final_verdict=f"MACD_REBOUND_DAILY_REPORT_READY|STATUS={scanner_status}|SCORE={health.health_score}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_report(report: DailyReport, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def render_report(report: DailyReport) -> str:
    lines = ["# MACD Rebound Daily Report", "",
        f"**report_id={report.report_id}**",
        f"**date={report.report_date}**",
        f"**status={report.scanner_status}**",
        f"**health_score={report.health_score}%**", "",
        "## Metrics", "",
        f"- total_signals: {report.total_signals}",
        f"- total_alerts: {report.total_alerts}",
        f"- failed_alerts: {report.failed_alerts}", "",
        "## Top Symbols", ""]
    for s in report.top_symbols[:5]:
        lines.append(f"- {s}")
    lines.extend(["", "## Anomalies", ""])
    for a in report.anomaly_summary:
        lines.append(f"- {a}")
    lines.extend(["", "## Suggested Actions", ""])
    for a in report.suggested_actions:
        lines.append(f"- {a}")
    lines.extend(["", "## Conclusion", "", report.final_verdict, ""])
    return "\n".join(lines)
