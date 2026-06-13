#!/usr/bin/env python3
"""T19501 — Run Alert Center Dry-Run.

Generates all Phase 4 reports and data files.
Dry-run only. No real notifications sent.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.alert_center import (
    build_alert_center_status,
    build_alert_event,
    build_heartbeat,
    classify_priority,
    compute_alerts_hash,
    deduplicate_alerts,
    format_feishu,
    render_status_markdown,
    write_json,
    write_manifest,
    write_markdown,
    write_status_json,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "alert_center"


def main() -> None:
    # Step 1: Generate sample alerts
    print("[1/5] Generating sample alerts...")
    sample_events = [
        {"source": "earnings", "priority": "IMPORTANT", "title": "AAPL Earnings Beat", "message": "AAPL beat estimates by 15%", "ticker": "AAPL"},
        {"source": "earnings", "priority": "IMPORTANT", "title": "MSFT Earnings Miss", "message": "MSFT missed by 3%", "ticker": "MSFT"},
        {"source": "stock_price", "priority": "WATCH", "title": "NVDA +5%", "message": "NVDA up 5% intraday", "ticker": "NVDA"},
        {"source": "stock_price", "priority": "WATCH", "title": "TSLA -3%", "message": "TSLA down 3%", "ticker": "TSLA"},
        {"source": "macd_rebound", "priority": "WATCH", "title": "SPY MACD Cross", "message": "SPY MACD bullish crossover", "ticker": "SPY"},
        {"source": "binance_futures", "priority": "IMPORTANT", "title": "BTC Volume Spike", "message": "BTC futures volume 3x average", "ticker": "BTCUSDT"},
        {"source": "binance_futures", "priority": "IMPORTANT", "title": "ETH Breakout", "message": "ETH above resistance", "ticker": "ETHUSDT"},
        {"source": "strategy_registry", "priority": "INFO", "title": "Strategy Update", "message": "macd_momentum_v1 moved to WATCHLIST", "ticker": ""},
        {"source": "system_heartbeat", "priority": "INFO", "title": "Heartbeat", "message": "System alive", "ticker": ""},
        {"source": "force_alert", "priority": "CRITICAL", "title": "Test Force Alert", "message": "Testing force alert mechanism", "ticker": ""},
        # Duplicate
        {"source": "earnings", "priority": "IMPORTANT", "title": "AAPL Earnings Beat", "message": "AAPL beat estimates by 15%", "ticker": "AAPL"},
    ]

    alerts = [build_alert_event(**e) for e in sample_events]
    print(f"  -> {len(alerts)} raw alerts ({sum(1 for a in alerts if a.is_duplicate)} duplicates)")

    # Step 2: Dedup
    print("[2/5] Deduplicating alerts...")
    deduped = deduplicate_alerts(alerts)
    print(f"  -> {len(deduped)} unique alerts")

    # Step 3: Feishu format (dry-run)
    print("[3/5] Formatting for Feishu (dry-run)...")
    feishu_cards = [format_feishu(a) for a in deduped]
    feishu_path = DATA_DIR / "feishu_dry_run_cards.jsonl"
    feishu_path.parent.mkdir(parents=True, exist_ok=True)
    feishu_path.write_text(
        json.dumps(feishu_cards, indent=2),
        encoding="utf-8",
    )
    print(f"  -> {len(feishu_cards)} Feishu cards generated (dry-run)")

    # Step 4: Heartbeat
    print("[4/5] Generating heartbeat...")
    active_sources = list({a.source for a in deduped})
    heartbeat = build_heartbeat(
        active_sources=active_sources,
        alert_count=len(alerts),
        duplicate_count=sum(1 for a in alerts if a.is_duplicate),
    )

    # Write all data
    write_json(deduped, DATA_DIR / "alerts.jsonl")
    write_json([heartbeat], DATA_DIR / "heartbeat.jsonl")

    # Step 5: Status report
    print("[5/5] Generating status report...")
    status = build_alert_center_status(deduped, heartbeat)
    write_status_json(status, REPORTS_DIR / "alert_center_status.json")

    status_md = render_status_markdown(status)
    write_markdown(status_md, REPORTS_DIR / "alert_center_status.md")

    # Dry-run report
    dry_run_md = [
        "# Alert Center Dry-Run Report",
        "",
        f"**Total raw alerts:** {len(alerts)}",
        f"**Unique alerts:** {len(deduped)}",
        f"**Duplicates filtered:** {sum(1 for a in alerts if a.is_duplicate)}",
        f"**Feishu cards generated:** {len(feishu_cards)}",
        f"**Active sources:** {', '.join(active_sources)}",
        f"**Heartbeat status:** {heartbeat.status}",
        "",
        "## Safety Boundary",
        "",
        "- All alerts are dry-run.",
        "- No real notifications sent.",
        "- No webhooks called.",
        "- No secrets exposed.",
        "",
        "---",
        "DRY RUN. NO REAL NOTIFICATIONS SENT.",
        "",
    ]
    write_markdown("\n".join(dry_run_md), REPORTS_DIR / "alert_center_dry_run_report.md")

    # Manifest
    write_manifest({
        "total_raw_alerts": len(alerts),
        "unique_alerts": len(deduped),
        "duplicates_filtered": sum(1 for a in alerts if a.is_duplicate),
        "feishu_cards": len(feishu_cards),
        "active_sources": active_sources,
        "dry_run": True,
        "alerts_hash": compute_alerts_hash(deduped),
    }, REPORTS_DIR / "alert_center_manifest.json")

    print(f"\nDONE. {len(deduped)} unique alerts, {len(feishu_cards)} Feishu cards.")
    print(f"Reports: {REPORTS_DIR}")
    print(f"Data: {DATA_DIR}")


if __name__ == "__main__":
    main()
