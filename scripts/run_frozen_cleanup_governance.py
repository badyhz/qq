#!/usr/bin/env python3
"""T17001 — Run Frozen Cleanup Governance Finalization.

Generates all Phase 1 reports, evidence, and data files.
Dry-run only. No actual file operations on frozen files.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_cleanup_decision_matrix import build_decision_matrix, write_json as write_decision_json, write_manifest as write_decision_manifest, write_markdown as write_decision_markdown
from core.frozen_cleanup_dry_run_executor import execute_cleanup_dry_run, write_json as write_dryrun_json, write_manifest as write_dryrun_manifest, write_markdown as write_dryrun_markdown
from core.frozen_cleanup_evidence_recorder import build_all_evidence, write_json as write_evidence_json, write_manifest as write_evidence_manifest, write_markdown as write_evidence_markdown
from core.frozen_cleanup_final_inventory import build_final_inventory, write_json as write_inventory_json, write_manifest as write_inventory_manifest, write_markdown as write_inventory_markdown
from core.frozen_cleanup_handoff_pack import build_handoff_pack, write_json as write_handoff_json, write_manifest as write_handoff_manifest, write_markdown as write_handoff_markdown
from core.frozen_cleanup_report import build_cleanup_report, write_json as write_report_json, write_manifest as write_report_manifest, write_markdown as write_report_markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "offline_frozen_cleanup"


def main() -> None:
    release_hold = "HOLD"

    # Source data
    backlog_records = [r.to_dict() for r in FROZEN_BACKLOG_INVENTORY.records]

    # Untracked frozen-related files from git status
    untracked_paths = [
        "core/live_runner.py",
        "scripts/live_playbook.py",
        "scripts/replay_shadow_order_plans_as_testnet_dry.py",
        "scripts/run_controlled_testnet_shift.py",
        "scripts/run_daily_shadow_scan_pipeline.py",
        "scripts/run_next_shadow_experiment_plan.py",
        "scripts/run_observation_shift_runtime.py",
        "scripts/run_remediation_shadow_only_loop.py",
        "scripts/run_replay_submit_batch.py",
        "scripts/run_right_breakout_param_observation.py",
        "scripts/run_right_breakout_scan_dry.py",
        "scripts/run_shadow_observation_experiments.py",
        "scripts/run_shadow_sample_collection_pipeline.py",
        "scripts/run_shadow_universe_collector.py",
        "scripts/run_signal_testnet_trial.py",
        "scripts/run_spot_testnet_acceptance.py",
        "scripts/safe_flatten_testnet_symbol.py",
        "scripts/submit_approved_candidates.py",
        "scripts/submit_replayed_testnet_payload.py",
        "scripts/verify_risk_release_flow.py",
        "scripts/verify_testnet_repair_scenarios.py",
    ]

    # External/research artifacts
    external_paths = [
        "docs/octopusycc_mouse_trade_plan_2026-05-23_2026-05-30.md",
    ]

    # Step 1: Final Inventory
    print("[1/6] Building final inventory...")
    inventory_items = build_final_inventory(backlog_records, untracked_paths, external_paths, release_hold)
    write_inventory_json(inventory_items, DATA_DIR / "final_inventory.jsonl")
    write_inventory_manifest(inventory_items, REPORTS_DIR / "offline_frozen_cleanup_final_inventory_manifest.json", release_hold)
    write_inventory_markdown(inventory_items, REPORTS_DIR / "offline_frozen_cleanup_final_inventory.md")
    print(f"  -> {len(inventory_items)} items inventoried")

    # Step 2: Decision Matrix
    print("[2/6] Building decision matrix...")
    decision_items = build_decision_matrix([i.to_dict() for i in inventory_items], release_hold)
    write_decision_json(decision_items, DATA_DIR / "decision_matrix.jsonl")
    write_decision_manifest(decision_items, REPORTS_DIR / "offline_frozen_cleanup_decision_matrix_manifest.json", release_hold)
    write_decision_markdown(decision_items, REPORTS_DIR / "offline_frozen_cleanup_decision_matrix.md")
    print(f"  -> {len(decision_items)} decisions generated")

    # Step 3: Dry-Run Executor
    print("[3/6] Executing cleanup dry-run...")
    dry_run_items = execute_cleanup_dry_run([d.to_dict() for d in decision_items], release_hold)
    write_dryrun_json(dry_run_items, DATA_DIR / "cleanup_dry_run.jsonl")
    write_dryrun_manifest(dry_run_items, REPORTS_DIR / "offline_frozen_cleanup_dry_run_manifest.json", release_hold)
    write_dryrun_markdown(dry_run_items, REPORTS_DIR / "offline_frozen_cleanup_dry_run_report.md")
    print(f"  -> {len(dry_run_items)} dry-run results")

    # Step 4: Evidence Recorder
    print("[4/6] Recording cleanup evidence...")
    evidence_items = build_all_evidence(
        [i.to_dict() for i in inventory_items],
        [d.to_dict() for d in decision_items],
        [r.to_dict() for r in dry_run_items],
        release_hold,
    )
    write_evidence_json(evidence_items, DATA_DIR / "cleanup_evidence.jsonl")
    write_evidence_manifest(evidence_items, REPORTS_DIR / "offline_frozen_cleanup_evidence_manifest.json", release_hold)
    write_evidence_markdown(evidence_items, REPORTS_DIR / "offline_frozen_cleanup_final_evidence.md")
    print(f"  -> {len(evidence_items)} evidence records")

    # Step 5: Final Report
    print("[5/6] Generating final cleanup report...")
    report = build_cleanup_report(
        [i.to_dict() for i in inventory_items],
        [d.to_dict() for d in decision_items],
        [r.to_dict() for r in dry_run_items],
        [e.to_dict() for e in evidence_items],
        release_hold,
    )
    write_report_json(report, REPORTS_DIR / "offline_frozen_cleanup_final_report.json")
    write_report_manifest(report, REPORTS_DIR / "offline_frozen_cleanup_final_report_manifest.json", release_hold)
    write_report_markdown(report, REPORTS_DIR / "offline_frozen_cleanup_final_report.md")
    print(f"  -> Report generated: {report.total_files_inventoried} files, {report.evidence_count} evidence records")

    # Step 6: Handoff Pack
    print("[6/6] Generating handoff pack...")
    pack = build_handoff_pack(
        "reports/offline_frozen_cleanup_final_inventory.md",
        "reports/offline_frozen_cleanup_decision_matrix.md",
        "reports/offline_frozen_cleanup_dry_run_report.md",
        "reports/offline_frozen_cleanup_final_evidence.md",
        "reports/offline_frozen_cleanup_final_report.md",
        release_hold,
    )
    write_handoff_json(pack, REPORTS_DIR / "offline_frozen_cleanup_handoff_pack.json")
    write_handoff_manifest(pack, REPORTS_DIR / "offline_frozen_cleanup_handoff_pack_manifest.json", release_hold)
    write_handoff_markdown(pack, REPORTS_DIR / "offline_frozen_cleanup_handoff_pack.md")
    print(f"  -> Handoff pack: {pack.total_artifacts} artifacts")

    print("\nDONE. All artifacts generated.")
    print(f"Reports: {REPORTS_DIR}")
    print(f"Data: {DATA_DIR}")
    print("NO ACTION PERFORMED. SIMULATION ONLY. HUMAN APPROVAL REQUIRED.")


if __name__ == "__main__":
    main()
