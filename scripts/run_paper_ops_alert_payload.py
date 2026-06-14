"""Runner: paper ops alert payload (dry-run only)."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_ops.log_freshness_monitor import check_freshness
from src.paper_trading_ops.paper_state_auditor import audit_store
from src.paper_trading_ops.strategy_quality_metrics import compute_metrics
from src.paper_trading_ops.signal_quality_dashboard import build_dashboard
from src.paper_trading_ops.daily_ops_bundle import build_ops_bundle
from src.paper_trading_ops.ops_alert_payload import generate_alert_payload
from src.paper_trading_pipeline.paper_position_store import load_store, DEFAULT_STORE_PATH
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.paper_trading_ops.models import LogFreshnessReport, new_id, utc_now_iso

OUT = pathlib.Path("reports/paper_trading_ops/alert_payload.json")


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
    payload = generate_alert_payload(bundle)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload.to_dict(), indent=2), encoding="utf-8")
    print(f"dry_run={payload.dry_run_only} verdict={payload.final_verdict}")


if __name__ == "__main__":
    main()
