"""T842: Runtime governance read-only manual review packet."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyManualReviewPacket:
    allowed_review_items: List[str] = field(default_factory=list)
    forbidden_actions: List[str] = field(default_factory=list)
    required_evidence: List[str] = field(default_factory=list)
    decision_options: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def build_readonly_manual_review_packet() -> RuntimeGovernanceReadOnlyManualReviewPacket:
    return RuntimeGovernanceReadOnlyManualReviewPacket(
        allowed_review_items=[
            "read-only hook spec",
            "permission envelope",
            "invariant checker",
            "side-effect declarations",
            "scenario catalog",
            "regression packet",
            "readiness score",
            "blocker summary",
            "evidence packet",
            "transition checklist",
        ],
        forbidden_actions=[
            "live trading",
            "order placement",
            "secret access",
            "exchange connection",
            "planner autonomous mode",
            "file write",
            "network call",
        ],
        required_evidence=[
            "permission envelope PASS",
            "invariant checker PASS",
            "side-effect declaration PASS",
            "scenario catalog PASS",
            "regression packet PASS",
            "readiness score >= B",
            "blocker summary PROCEED",
            "evidence packet PASS",
            "transition checklist complete",
        ],
        decision_options=[
            "APPROVE_READONLY_DESIGN_ONLY",
            "REQUEST_CHANGES",
        ],
        notes=[
            "Approval is for read-only design only.",
            "Does not authorize live trading.",
            "Does not authorize order placement.",
        ],
    )


def readonly_manual_review_packet_to_dict(
    packet: RuntimeGovernanceReadOnlyManualReviewPacket,
) -> Dict:
    return {
        "allowed_review_items": list(packet.allowed_review_items),
        "forbidden_actions": list(packet.forbidden_actions),
        "required_evidence": list(packet.required_evidence),
        "decision_options": list(packet.decision_options),
        "notes": list(packet.notes),
    }


def readonly_manual_review_packet_to_markdown(
    packet: RuntimeGovernanceReadOnlyManualReviewPacket,
) -> str:
    lines = ["# Runtime Governance Read-Only Manual Review Packet", ""]

    lines.append("## Allowed Review Items")
    for item in packet.allowed_review_items:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Forbidden Actions")
    for action in packet.forbidden_actions:
        lines.append(f"- {action}")
    lines.append("")

    lines.append("## Required Evidence")
    for evidence in packet.required_evidence:
        lines.append(f"- {evidence}")
    lines.append("")

    lines.append("## Decision Options")
    for option in packet.decision_options:
        lines.append(f"- {option}")
    lines.append("")

    lines.append("## Notes")
    for note in packet.notes:
        lines.append(f"- {note}")
    lines.append("")

    return "\n".join(lines)
