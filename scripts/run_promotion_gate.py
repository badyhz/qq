#!/usr/bin/env python3
"""T17501 — Run Shadow-to-Testnet Promotion Gate.

Generates all Phase 2 reports and data files.
Dry-run only. No real testnet submit.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.promotion_evidence_loader import load_all_promotion_evidence, compute_evidence_hash
from core.promotion_decision_engine import (
    make_promotion_decision,
    write_json as write_decision_json,
    write_manifest as write_decision_manifest,
    write_markdown as write_decision_markdown,
    render_denial_reasons_markdown,
    DenialReason,
)
from core.promotion_approval_packet import (
    build_approval_packet,
    write_json as write_packet_json,
    write_manifest as write_packet_manifest,
    write_markdown as write_packet_markdown,
)
from core.promotion_rollback_plan import (
    build_rollback_plan,
    write_json as write_rollback_json,
    write_manifest as write_rollback_manifest,
    write_markdown as write_rollback_markdown,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "promotion"


def main() -> None:
    release_hold = "HOLD"

    # Evidence sources (simulated — all passing for dry-run)
    cleanup_report = {"cleanup_ready_for_human_review": True}
    shadow_data = {"shadow_evidence_exists": True, "stability_score": 0.85}
    safety_data = {"no_submit_guard_passed": True}
    regression_data = {"offline_regression_clean": True}
    registry_data = {"strategy_registry_exists": True}
    testnet_data = {"testnet_dry_run_no_submit_default": True}

    # Step 1: Load evidence
    print("[1/5] Loading promotion evidence...")
    evidence = load_all_promotion_evidence(
        cleanup_report, shadow_data, safety_data,
        regression_data, registry_data, testnet_data,
        release_hold,
    )
    evidence_path = DATA_DIR / "promotion_evidence.jsonl"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps([e.to_dict() for e in evidence], indent=2),
        encoding="utf-8",
    )
    print(f"  -> {len(evidence)} evidence items loaded")

    # Step 2: Make decision
    print("[2/5] Making promotion decision...")
    decision = make_promotion_decision([e.to_dict() for e in evidence], release_hold)
    write_decision_json(decision, DATA_DIR / "shadow_to_testnet_decision.json")
    write_decision_manifest(decision, REPORTS_DIR / "shadow_to_testnet_promotion_decision_manifest.json", release_hold)
    write_decision_markdown(decision, REPORTS_DIR / "shadow_to_testnet_promotion_decision.md")
    print(f"  -> Decision: {decision.decision}")

    # Step 3: Denial reasons
    print("[3/5] Generating denial reasons report...")
    denials = [DenialReason(
        reason_id=f"denial_{d}",
        evidence_type=d,
        description=f"evidence_{d}_failed",
        blocking=True,
    ) for d in decision.evidence_failed]
    denial_path = REPORTS_DIR / "shadow_to_testnet_denial_reasons.md"
    denial_path.parent.mkdir(parents=True, exist_ok=True)
    denial_path.write_text(render_denial_reasons_markdown(denials), encoding="utf-8")
    print(f"  -> {len(denials)} denial reasons")

    # Step 4: Approval packet + rollback plan
    print("[4/5] Generating approval packet and rollback plan...")
    packet = build_approval_packet(decision.to_dict(), release_hold)
    write_packet_json(packet, REPORTS_DIR / "shadow_to_testnet_approval_packet.json")
    write_packet_manifest(packet, REPORTS_DIR / "shadow_to_testnet_approval_packet_manifest.json", release_hold)
    write_packet_markdown(packet, REPORTS_DIR / "shadow_to_testnet_approval_packet.md")

    rollback = build_rollback_plan(release_hold)
    write_rollback_json(rollback, REPORTS_DIR / "shadow_to_testnet_rollback_plan.json")
    write_rollback_manifest(rollback, REPORTS_DIR / "shadow_to_testnet_rollback_plan_manifest.json", release_hold)
    write_rollback_markdown(rollback, REPORTS_DIR / "shadow_to_testnet_rollback_plan.md")
    print(f"  -> Approval packet: {packet.total_items} items")
    print(f"  -> Rollback plan: {rollback.total_steps} steps")

    # Step 5: Promotion matrix report
    print("[5/5] Generating promotion matrix report...")
    matrix_path = REPORTS_DIR / "shadow_to_testnet_promotion_matrix.md"
    lines = [
        "# Shadow-to-Testnet Promotion Matrix",
        "",
        f"**Decision:** {decision.decision}",
        f"**Evidence passed:** {len(decision.evidence_passed)}",
        f"**Evidence failed:** {len(decision.evidence_failed)}",
        f"**simulation_only:** {decision.simulation_only}",
        "",
        "## Evidence Types",
        "",
    ]
    for e in evidence:
        lines.append(f"- **{e.evidence_type}:** {e.status} (verified={e.verified})")
    lines.append("")
    lines.append("---")
    lines.append("SIMULATION ONLY. NO SUBMIT AUTHORIZED.")
    lines.append("")
    matrix_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nDONE. Decision: {decision.decision}")
    print(f"Reports: {REPORTS_DIR}")
    print(f"Data: {DATA_DIR}")


if __name__ == "__main__":
    main()
