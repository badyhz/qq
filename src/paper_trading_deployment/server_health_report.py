"""Server health report — aggregates deployment status."""
from __future__ import annotations
import json, pathlib
from src.paper_trading_deployment.models import ServerHealthReport, new_id, utc_now_iso
from src.paper_trading_deployment.server_config import build_server_config
from src.paper_trading_deployment.preflight_check import run_preflight
from src.paper_trading_deployment.runtime_layout import check_layout


def _load_latest_report(reports_dir: pathlib.Path, name: str) -> dict | None:
    target = reports_dir / f"{name}.json"
    if target.exists():
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def generate_health_report(repo_path: str | None = None) -> ServerHealthReport:
    cfg = build_server_config()
    repo = repo_path or cfg.repo_path

    preflight = run_preflight(repo, cfg.scanner_path)
    layout = check_layout(repo)

    reports_dir = pathlib.Path(repo) / cfg.reports_dir
    latest_bundle = _load_latest_report(reports_dir, "daily_bundle")
    latest_metrics = _load_latest_report(reports_dir, "strategy_metrics")
    latest_dashboard = _load_latest_report(reports_dir, "signal_dashboard")

    paper_ops_status = "NO_DATA"
    strategy_quality_status = "NO_DATA"

    if latest_bundle:
        verdict = latest_bundle.get("final_verdict", "")
        if "HEALTHY" in verdict:
            paper_ops_status = "HEALTHY"
        elif "WARNING" in verdict:
            paper_ops_status = "WARNING"
        elif "CRITICAL" in verdict:
            paper_ops_status = "CRITICAL"

    if latest_metrics:
        sample = latest_metrics.get("sample_status", "")
        if sample:
            strategy_quality_status = sample

    # Health score
    score = 100
    actions: list[str] = []

    if preflight.preflight_status == "FAIL":
        score -= 30
        actions.append("Fix preflight failures")
    if layout.layout_status == "INCOMPLETE":
        score -= 20
        actions.append("Create missing runtime directories")
    if paper_ops_status == "CRITICAL":
        score -= 30
        actions.append("Address critical paper ops alerts")
    elif paper_ops_status == "WARNING":
        score -= 10
        actions.append("Review paper ops warnings")
    if strategy_quality_status == "WEAK":
        score -= 15
        actions.append("Strategy quality is weak — review signals")
    if not latest_bundle:
        score -= 10
        actions.append("Run daily paper ops bundle")

    if not actions:
        actions.append("Continue monitoring")

    health_status = "HEALTHY" if score >= 80 else ("DEGRADED" if score >= 50 else "UNHEALTHY")

    return ServerHealthReport(
        health_id=new_id("SHR"), created_at=utc_now_iso(),
        server_alias=cfg.host_alias, repo_path=repo,
        scanner_path=cfg.scanner_path,
        preflight_status=preflight.preflight_status,
        runtime_layout_status=layout.layout_status,
        paper_ops_status=paper_ops_status,
        strategy_quality_status=strategy_quality_status,
        health_score=max(0, score), health_status=health_status,
        recommended_actions=actions,
        final_verdict=f"PAPER_OPS_SERVER_HEALTH_REPORT_READY|SCORE={max(0, score)}|STATUS={health_status}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
