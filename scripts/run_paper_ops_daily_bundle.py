"""Runner: paper ops daily bundle."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_ops.log_freshness_monitor import check_freshness
from src.paper_trading_ops.paper_state_auditor import audit_store
from src.paper_trading_ops.strategy_quality_metrics import compute_metrics
from src.paper_trading_ops.signal_quality_dashboard import build_dashboard
from src.paper_trading_ops.daily_ops_bundle import build_ops_bundle
from src.paper_trading_pipeline.paper_position_store import load_store, DEFAULT_STORE_PATH
from src.external_scanner_integrations.macd_rebound_config import create_config

OUT = pathlib.Path("reports/paper_trading_ops/daily_bundle.json")
MD_OUT = pathlib.Path("reports/paper_trading_ops/daily_bundle.md")


def main() -> None:
    cfg = create_config()
    freshness = check_freshness(cfg.local_path) if cfg.local_path else None
    state_audit = audit_store(DEFAULT_STORE_PATH)
    records = load_store()
    positions = [r.to_dict() for r in records]
    metrics = compute_metrics(positions)
    dashboard = build_dashboard(
        raw_signals=0, deduped_signals=0, plans_created=0, plans_rejected=0,
        positions=positions, expectancy_r=metrics.expectancy_r, win_rate=metrics.win_rate,
    )
    if freshness is None:
        from src.paper_trading_ops.models import LogFreshnessReport, new_id, utc_now_iso
        freshness = LogFreshnessReport(
            report_id=new_id("LFR"), created_at=utc_now_iso(), scanner_path="",
            signals_file_exists=False, alerts_file_exists=False,
            scan_detail_file_exists=False, errors_file_exists=False,
            latest_signal_time=None, latest_alert_time=None, latest_scan_detail_time=None,
            minutes_since_latest_signal=None, minutes_since_latest_alert=None,
            minutes_since_latest_scan_detail=None,
            freshness_status="NO_DATA", stale_reasons=["Scanner path not configured"],
            final_verdict="NO_DATA",
        )
    bundle = build_ops_bundle(freshness, state_audit, metrics, dashboard)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")
    # Markdown
    md_lines = [
        f"# Daily Paper Ops Bundle {bundle.date}", "",
        f"**Status:** {bundle.freshness_status} / {bundle.paper_state_status} / {bundle.strategy_sample_status}",
        f"**Dashboard Grade:** {bundle.dashboard_grade}", "",
    ]
    if bundle.critical_alerts:
        md_lines.append("## Critical Alerts")
        for a in bundle.critical_alerts:
            md_lines.append(f"- {a}")
        md_lines.append("")
    if bundle.warnings:
        md_lines.append("## Warnings")
        for w in bundle.warnings:
            md_lines.append(f"- {w}")
        md_lines.append("")
    md_lines.append("## Recommended Actions")
    for a in bundle.recommended_actions:
        md_lines.append(f"- {a}")
    md_lines.append("")
    md_lines.append(f"**Verdict:** `{bundle.final_verdict}`")
    MD_OUT.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"verdict={bundle.final_verdict}")


if __name__ == "__main__":
    main()
