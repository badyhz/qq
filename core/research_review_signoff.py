"""Research review signoff — signoff template and validator.

Program C: Signoff Template.
Program D: Signoff Validator.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

SIGNOFF_VERSION = "1.0.0"

ALLOWED_MANUAL_DECISIONS = (
    "REJECT",
    "REQUEST_MORE_RESEARCH",
    "ACCEPT_ADVISORY_RESEARCH_ONLY",
)

DISALLOWED_DECISIONS = (
    "APPROVE_LIVE",
    "APPROVE_TESTNET_SUBMIT",
    "APPROVE_RUNTIME",
    "APPROVE_PLANNER_INTEGRATION",
    "AUTO_PROMOTE",
)


def build_signoff_template(packet_id: str = "") -> Dict[str, Any]:
    """Build signoff template JSON."""
    return {
        "schema_version": "1.0.0",
        "signoff_version": SIGNOFF_VERSION,
        "reviewer_name": "",
        "reviewer_role": "",
        "review_date": "",
        "reviewed_packet_id": packet_id,
        "decision": "",
        "decision_reason": "",
        "unresolved_blockers": [],
        "accepted_risks": [],
        "rejected_promotions": list(DISALLOWED_DECISIONS),
        "confirmation_release_hold_remains_HOLD": False,
        "confirmation_advisory_only": False,
        "confirmation_no_live_testnet_runtime": False,
        "signature_placeholder": "<REVIEWER_SIGNATURE>",
        "allowed_decisions": list(ALLOWED_MANUAL_DECISIONS),
        "disallowed_decisions": list(DISALLOWED_DECISIONS),
    }


def render_signoff_markdown(template: Dict[str, Any]) -> str:
    """Render signoff template as markdown."""
    lines: List[str] = []
    lines.append("# Review Signoff Template")
    lines.append("")
    lines.append(f"Version: {template.get('signoff_version', 'unknown')}")
    lines.append(f"Reviewed packet: {template.get('reviewed_packet_id', '')}")
    lines.append("")
    lines.append("## Reviewer Information")
    lines.append("")
    lines.append(f"- **Name:** {template.get('reviewer_name', '') or '<FILL IN>'}")
    lines.append(f"- **Role:** {template.get('reviewer_role', '') or '<FILL IN>'}")
    lines.append(f"- **Date:** {template.get('review_date', '') or '<FILL IN>'}")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- **Decision:** {template.get('decision', '') or '<SELECT>'}")
    lines.append(f"- **Reason:** {template.get('decision_reason', '') or '<FILL IN>'}")
    lines.append("")
    lines.append("Allowed decisions:")
    for d in ALLOWED_MANUAL_DECISIONS:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("**Forbidden decisions (never allowed):**")
    for d in DISALLOWED_DECISIONS:
        lines.append(f"- ~~{d}~~")
    lines.append("")
    lines.append("## Unresolved Blockers")
    lines.append("")
    blockers = template.get("unresolved_blockers", [])
    if blockers:
        for b in blockers:
            lines.append(f"- {b}")
    else:
        lines.append("- None / <LIST IF ANY>")
    lines.append("")
    lines.append("## Accepted Risks")
    lines.append("")
    risks = template.get("accepted_risks", [])
    if risks:
        for r in risks:
            lines.append(f"- {r}")
    else:
        lines.append("- None / <LIST IF ANY>")
    lines.append("")
    lines.append("## Confirmations")
    lines.append("")
    lines.append(f"- [ ] release_hold remains HOLD: {template.get('confirmation_release_hold_remains_HOLD', False)}")
    lines.append(f"- [ ] Advisory only: {template.get('confirmation_advisory_only', False)}")
    lines.append(f"- [ ] No live/testnet/runtime: {template.get('confirmation_no_live_testnet_runtime', False)}")
    lines.append("")
    lines.append("## Signature")
    lines.append("")
    lines.append(f"{template.get('signature_placeholder', '<REVIEWER_SIGNATURE>')}")
    lines.append("")

    return "\n".join(lines)


def validate_completed_signoff(signoff: Dict[str, Any]) -> Tuple[bool, Tuple[str, ...]]:
    """Validate a completed signoff JSON.

    Program D: Signoff Validator.
    """
    errors: List[str] = []

    # Required fields
    if not signoff.get("reviewer_name", "").strip():
        errors.append("missing reviewer_name")

    if not signoff.get("decision", "").strip():
        errors.append("missing decision")

    # Decision validation
    decision = signoff.get("decision", "")
    if decision and decision not in ALLOWED_MANUAL_DECISIONS:
        errors.append(f"decision {decision!r} not in allowed manual decisions")

    if decision in DISALLOWED_DECISIONS:
        errors.append(f"decision {decision!r} is explicitly disallowed")

    # Confirmation flags
    if not signoff.get("confirmation_release_hold_remains_HOLD", False):
        errors.append("confirmation_release_hold_remains_HOLD must be true")

    if not signoff.get("confirmation_advisory_only", False):
        errors.append("confirmation_advisory_only must be true")

    if not signoff.get("confirmation_no_live_testnet_runtime", False):
        errors.append("confirmation_no_live_testnet_runtime must be true")

    # Unresolved blocker rules
    unresolved = signoff.get("unresolved_blockers", [])
    if unresolved:
        if decision == "ACCEPT_ADVISORY_RESEARCH_ONLY":
            # Check if any critical blockers
            critical = [b for b in unresolved if isinstance(b, dict) and b.get("severity") == "CRITICAL"]
            if critical:
                errors.append(
                    "ACCEPT_ADVISORY_RESEARCH_ONLY not allowed with critical unresolved blockers"
                )
        if decision not in ("REJECT", "REQUEST_MORE_RESEARCH"):
            errors.append(
                f"unresolved blockers present but decision is {decision!r} "
                "(must be REJECT or REQUEST_MORE_RESEARCH)"
            )

    # Must never produce live/testnet/runtime approval
    forbidden_present = [d for d in (decision,) if d in DISALLOWED_DECISIONS]
    if forbidden_present:
        errors.append(f"signoff contains forbidden decision: {forbidden_present}")

    return (len(errors) == 0, tuple(errors))


def validate_signoff_template_safety(template: Dict[str, Any]) -> Tuple[bool, Tuple[str, ...]]:
    """Validate signoff template safety (no completed decision required)."""
    errors: List[str] = []

    # Check disallowed decisions list is present and correct
    disallowed = template.get("disallowed_decisions", [])
    for dd in DISALLOWED_DECISIONS:
        if dd not in disallowed:
            errors.append(f"disallowed_decisions missing {dd}")

    # Check allowed decisions exclude disallowed
    allowed = set(template.get("allowed_decisions", []))
    for dd in DISALLOWED_DECISIONS:
        if dd in allowed:
            errors.append(f"disallowed decision {dd} found in allowed_decisions")

    return (len(errors) == 0, tuple(errors))
