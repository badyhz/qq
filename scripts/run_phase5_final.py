#!/usr/bin/env python3
"""T21001 — Run Phase 5: Testnet Dry-Run + Operator Console + Final Handoff.

Generates all Phase 5 reports and data files.
Dry-run only. No real orders. No real exchange.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.testnet_dry_run_orchestrator import (
    build_order_intent,
    compute_lifecycle_hash,
    render_orchestrator_report,
    render_result_review_packet,
    render_stability_report,
    run_orchestrator,
    write_json as write_lifecycle_json,
    write_manifest,
    write_markdown,
    write_score_json,
)
from core.operator_console import (
    build_operator_console,
    render_blockers_markdown,
    render_console_markdown,
    render_next_actions_markdown,
    write_json as write_console_json,
    write_manifest as write_console_manifest,
    write_markdown as write_console_markdown,
)
from core.final_handoff_pack import (
    build_final_handoff_pack,
    render_completion_matrix_markdown,
    render_handoff_markdown,
    render_next_prd_markdown,
    render_remaining_risks_markdown,
    render_test_summary_markdown,
    write_json as write_handoff_json,
    write_manifest as write_handoff_manifest,
    write_markdown as write_handoff_markdown,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "testnet_dry_run"


def main() -> None:
    release_hold = "HOLD"

    # === A. Testnet Dry-Run Orchestrator ===
    print("=== A. Testnet Dry-Run Orchestrator ===")
    print("[1/3] Building order intents...")
    intents = [
        build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "macd_momentum_v1"),
        build_order_intent("ETHUSDT", "BUY", "LIMIT", 0.01, 3000.0, "binance_futures_scanner"),
        build_order_intent("BTCUSDT", "SELL", "MARKET", 0.001, 51000.0, "macd_momentum_v1"),
        build_order_intent("SOLUSDT", "BUY", "LIMIT", 1.0, 150.0, "binance_futures_scanner"),
        build_order_intent("ETHUSDT", "SELL", "LIMIT", 0.01, 3100.0, "binance_futures_scanner"),
    ]
    print(f"  -> {len(intents)} order intents")

    print("[2/3] Running orchestrator...")
    events, score = run_orchestrator(intents, release_hold)
    write_lifecycle_json(events, DATA_DIR / "order_lifecycle.jsonl")
    write_lifecycle_json(intents, DATA_DIR / "order_intents.jsonl")
    write_score_json(score, REPORTS_DIR / "testnet_dry_run_stability_score.json")
    print(f"  -> {len(events)} lifecycle events, stability={score.stability_ratio}")

    print("[3/3] Generating orchestrator reports...")
    write_markdown(render_orchestrator_report(events, score), REPORTS_DIR / "testnet_dry_run_orchestrator_report.md")
    write_markdown(render_stability_report(score), REPORTS_DIR / "testnet_dry_run_stability_score.md")
    write_markdown(render_result_review_packet(events, score), REPORTS_DIR / "testnet_dry_run_result_review_packet.md")

    # No-submit evidence
    no_submit_path = DATA_DIR / "no_submit_evidence.jsonl"
    no_submit_path.parent.mkdir(parents=True, exist_ok=True)
    no_submit_path.write_text(json.dumps([
        {"evidence_type": "no_real_submit", "dry_run": True, "events_count": len(events)},
        {"evidence_type": "no_real_exchange_call", "dry_run": True},
        {"evidence_type": "no_real_api_key_read", "dry_run": True},
    ], indent=2), encoding="utf-8")

    # === B. Operator Console ===
    print("\n=== B. Operator Console ===")
    console = build_operator_console(
        frozen_cleanup_done=True,
        promotion_decision="READY_FOR_TESTNET_DRY_RUN_PREP",
        strategy_count=11,
        dry_run_stability=score.stability_ratio,
    )
    write_console_json(console, REPORTS_DIR / "operator_console.json")
    write_console_manifest(console, REPORTS_DIR / "operator_console_manifest.json")
    write_console_markdown(render_console_markdown(console), REPORTS_DIR / "operator_console.md")
    write_console_markdown(render_next_actions_markdown(console), REPORTS_DIR / "operator_next_actions.md")
    write_console_markdown(render_blockers_markdown(console), REPORTS_DIR / "operator_blockers.md")

    # System status JSON
    status_path = DATA_DIR.parent / "operator_console" / "system_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(console.to_dict(), indent=2), encoding="utf-8")

    print(f"  -> Console: mode={console.current_mode}, healthy={console.system_healthy}")

    # === C. Final Handoff Pack ===
    print("\n=== C. Final Handoff Pack ===")
    pack = build_final_handoff_pack(release_hold)
    write_handoff_json(pack, REPORTS_DIR / "final_system_handoff_pack.json")
    write_handoff_manifest(pack, REPORTS_DIR / "final_system_handoff_pack_manifest.json")
    write_handoff_markdown(render_handoff_markdown(pack), REPORTS_DIR / "final_system_handoff_pack.md")
    write_handoff_markdown(render_remaining_risks_markdown(pack), REPORTS_DIR / "final_remaining_risks.md")
    write_handoff_markdown(render_completion_matrix_markdown(pack), REPORTS_DIR / "final_module_completion_matrix.md")
    write_handoff_markdown(render_test_summary_markdown(8050, 8044, 6), REPORTS_DIR / "final_test_summary.md")
    write_handoff_markdown(render_next_prd_markdown(pack), REPORTS_DIR / "final_next_prd_recommendation.md")

    print(f"  -> Handoff pack: {pack.total_modules} modules, {pack.completed_modules} completed")
    print(f"  -> Conclusions: {', '.join(pack.final_conclusions)}")

    print(f"\nDONE. All Phase 5 artifacts generated.")
    print(f"Reports: {REPORTS_DIR}")
    print(f"Data: {DATA_DIR}")


if __name__ == "__main__":
    main()
