"""Research review checklist — generate human review checklist.

Program B: Human Review Checklist.
Generates review_checklist.json and review_checklist.md.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

REVIEW_CHECKLIST_VERSION = "1.0.0"

CHECKLIST_ITEMS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "safety_flags_verified",
        "label": "Safety flags verified (no_live, no_submit, no_exchange, no_network)",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> safety fields",
        "failure_impact": "Safety boundary violation — review cannot proceed",
    },
    {
        "id": "release_hold_verified",
        "label": "release_hold verified as HOLD",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> release_hold",
        "failure_impact": "Release hold not confirmed — review cannot proceed",
    },
    {
        "id": "advisory_only_verified",
        "label": "advisory_only verified as True",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> advisory_only",
        "failure_impact": "Advisory-only not confirmed — review cannot proceed",
    },
    {
        "id": "human_review_required_verified",
        "label": "human_review_required verified as True",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> human_review_required",
        "failure_impact": "Human review requirement not confirmed",
    },
    {
        "id": "quality_gate_reviewed",
        "label": "Quality gate output reviewed",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> quality_verdict",
        "failure_impact": "Quality gate verdict not inspected",
    },
    {
        "id": "artifact_browser_reviewed",
        "label": "Artifact browser output reviewed",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> browser_verdict",
        "failure_impact": "Artifact browser verdict not inspected",
    },
    {
        "id": "comparison_analytics_reviewed",
        "label": "Comparison analytics output reviewed",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> comparison_verdict",
        "failure_impact": "Comparison verdict not inspected",
    },
    {
        "id": "blockers_reviewed",
        "label": "Blockers reviewed and understood",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> blockers",
        "failure_impact": "Blockers not inspected — cannot make informed decision",
    },
    {
        "id": "warnings_reviewed",
        "label": "Warnings reviewed and understood",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> warnings",
        "failure_impact": "Warnings not inspected",
    },
    {
        "id": "negative_controls_reviewed",
        "label": "Negative controls reviewed (random/shuffled/inverted baselines)",
        "required": True,
        "status": "PENDING",
        "evidence_path": "quality_gate/negative_control_report.json",
        "failure_impact": "Negative control results not inspected",
    },
    {
        "id": "bootstrap_uncertainty_reviewed",
        "label": "Bootstrap uncertainty intervals reviewed",
        "required": True,
        "status": "PENDING",
        "evidence_path": "quality_gate/bootstrap_confidence_intervals.json",
        "failure_impact": "Bootstrap uncertainty not inspected",
    },
    {
        "id": "regime_risk_reviewed",
        "label": "Regime breakdown / failure report reviewed",
        "required": True,
        "status": "PENDING",
        "evidence_path": "quality_gate/regime_breakdown.json",
        "failure_impact": "Regime risk not inspected",
    },
    {
        "id": "portfolio_overlap_reviewed",
        "label": "Portfolio overlap risk reviewed",
        "required": True,
        "status": "PENDING",
        "evidence_path": "quality_gate/portfolio_overlap_risk.json",
        "failure_impact": "Portfolio overlap risk not inspected",
    },
    {
        "id": "reproducibility_reviewed",
        "label": "Reproducibility manifest reviewed",
        "required": True,
        "status": "PENDING",
        "evidence_path": "quality_gate/reproducibility_manifest.json",
        "failure_impact": "Reproducibility not verified",
    },
    {
        "id": "artifact_hashes_reviewed",
        "label": "Artifact hashes reviewed for integrity",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_manifest.json -> source_hashes, output_hashes",
        "failure_impact": "Artifact integrity not verified",
    },
    {
        "id": "no_runtime_testnet_live_escalation_confirmed",
        "label": "Confirmed: no runtime/testnet/live escalation permitted",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_packet.json -> forbidden_decisions",
        "failure_impact": "Escalation boundary not confirmed",
    },
    {
        "id": "final_manual_decision_recorded",
        "label": "Final manual decision recorded in signoff",
        "required": True,
        "status": "PENDING",
        "evidence_path": "review_signoff_template.json",
        "failure_impact": "No decision recorded — review incomplete",
    },
)


def build_review_checklist(
    source_verdicts: Dict[str, str] = None,
) -> Dict[str, Any]:
    """Build review checklist JSON."""
    items = []
    for item in CHECKLIST_ITEMS:
        entry = dict(item)
        items.append(entry)

    return {
        "schema_version": "1.0.0",
        "checklist_version": REVIEW_CHECKLIST_VERSION,
        "total_items": len(items),
        "required_items": sum(1 for i in items if i["required"]),
        "pending_items": sum(1 for i in items if i["status"] == "PENDING"),
        "items": items,
    }


def render_checklist_markdown(checklist: Dict[str, Any]) -> str:
    """Render checklist as markdown."""
    lines: List[str] = []
    lines.append("# Human Review Checklist")
    lines.append("")
    lines.append(f"Version: {checklist.get('checklist_version', 'unknown')}")
    lines.append(f"Total items: {checklist.get('total_items', 0)}")
    lines.append(f"Required items: {checklist.get('required_items', 0)}")
    lines.append(f"Pending items: {checklist.get('pending_items', 0)}")
    lines.append("")
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- release_hold = HOLD")
    lines.append("- advisory_only = True")
    lines.append("- human_review_required = True")
    lines.append("- no_live = True")
    lines.append("- no_submit = True")
    lines.append("- no_exchange = True")
    lines.append("- no_network = True")
    lines.append("- no_runtime_integration = True")
    lines.append("- no_planner_integration = True")
    lines.append("")
    lines.append("## Checklist Items")
    lines.append("")

    for idx, item in enumerate(checklist.get("items", []), 1):
        status = item.get("status", "PENDING")
        marker = "[ ]" if status == "PENDING" else "[x]"
        req = " **REQUIRED**" if item.get("required") else ""
        lines.append(f"{idx}. {marker} {item.get('label', '')}{req}")
        lines.append(f"   - ID: `{item.get('id', '')}`")
        lines.append(f"   - Evidence: `{item.get('evidence_path', '')}`")
        lines.append(f"   - Failure impact: {item.get('failure_impact', '')}")
        lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append("After completing all items, record your decision in the signoff template.")
    lines.append("")
    lines.append("Allowed decisions:")
    lines.append("- REJECT")
    lines.append("- REQUEST_MORE_RESEARCH")
    lines.append("- ACCEPT_ADVISORY_RESEARCH_ONLY")
    lines.append("")
    lines.append("Forbidden decisions (never allowed):")
    lines.append("- APPROVE_LIVE")
    lines.append("- APPROVE_TESTNET_SUBMIT")
    lines.append("- APPROVE_RUNTIME")
    lines.append("- APPROVE_PLANNER_INTEGRATION")
    lines.append("- AUTO_PROMOTE")
    lines.append("")

    return "\n".join(lines)


def validate_checklist_shape(checklist: Dict[str, Any]) -> Tuple[bool, Tuple[str, ...]]:
    """Validate checklist has required shape."""
    errors: List[str] = []
    items = checklist.get("items", [])
    if not items:
        errors.append("checklist has no items")
        return (False, tuple(errors))

    required_ids = {i["id"] for i in CHECKLIST_ITEMS}
    actual_ids = {i.get("id") for i in items}
    missing = required_ids - actual_ids
    if missing:
        errors.append(f"missing checklist items: {sorted(missing)}")

    for item in items:
        if "id" not in item:
            errors.append("item missing id")
        if "label" not in item:
            errors.append(f"item {item.get('id', '?')} missing label")
        if "status" not in item:
            errors.append(f"item {item.get('id', '?')} missing status")

    return (len(errors) == 0, tuple(errors))
