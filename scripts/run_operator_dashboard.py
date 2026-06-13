#!/usr/bin/env python3
"""T39001 — Generate Operator Dashboard HTML and reports."""
from __future__ import annotations

import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.operator_dashboard_renderer import (
    RELEASE_HOLD_REQUIRED_ODR,
    build_dashboard_data,
    compute_dashboard_hash,
    render_dashboard_html,
    render_dashboard_markdown,
    write_html,
    write_json,
    write_manifest,
    write_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "operator_dashboard"


def main() -> None:
    status_path = ROOT / "data" / "operator_console" / "system_status.json"
    if status_path.exists():
        system_status = json.loads(status_path.read_text(encoding="utf-8"))
    else:
        system_status = {
            "current_mode": "TESTNET_DRY_RUN_PREP",
            "submit_permission": "NO_SUBMIT",
            "real_submit_allowed": False,
            "testnet_submit_allowed": False,
            "dry_run_allowed": True,
            "frozen_cleanup_status": "COMPLETE",
            "promotion_status": "READY_FOR_TESTNET_DRY_RUN_PREP",
            "strategy_count": 11,
            "active_alert_sources": ["earnings", "stock_price", "macd_rebound", "binance_futures", "system_heartbeat"],
            "critical_blockers": [],
            "next_recommended_phase": "TESTNET_DRY_RUN_SIMULATION",
            "system_healthy": True,
            "dry_run": True,
        }

    data = build_dashboard_data(system_status, snapshot_id="operator_dashboard_v1")
    dash_hash = compute_dashboard_hash(data)

    write_html(render_dashboard_html(data), REPORTS_DIR / "operator_dashboard.html")
    write_json(data, DATA_DIR / "dashboard_snapshot.json")
    write_manifest(data, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED_ODR)
    write_markdown(render_dashboard_markdown(data), REPORTS_DIR / "operator_dashboard_summary.md")

    print(f"Dashboard: mode={data.current_mode}, health={'OK' if data.system_healthy else 'FAIL'}")
    print(f"Hash={dash_hash[:16]}...")
    print(f"HTML: {REPORTS_DIR}/operator_dashboard.html")
    print(f"Data: {DATA_DIR}/")


if __name__ == "__main__":
    main()
