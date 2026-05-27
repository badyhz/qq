"""T1122 - Human Review Checklist Renderer."""
from __future__ import annotations

from core.human_review_evidence_checklist import HumanReviewEvidenceChecklist
from core.human_review_forbidden_approval import HumanReviewForbiddenApproval
from core.human_review_approval_state import HumanReviewApprovalState


def render_evidence_checklist_md(checklist: HumanReviewEvidenceChecklist) -> str:
    lines: list[str] = []
    lines.append("## Evidence Checklist")
    lines.append("")
    lines.append(f"- **Gate ID:** {checklist.gate_id}")
    lines.append(f"- **Item Count:** {len(checklist.items)}")
    lines.append("")
    if checklist.items:
        lines.append("### Items")
        for item in checklist.items:
            req = "required" if item.required else "optional"
            status = "verified" if item.verified else "unverified"
            lines.append(f"- **{item.name}** [{req}] [{status}]")
        lines.append("")
    return "\n".join(lines)


def render_forbidden_approval_md(forbidden: HumanReviewForbiddenApproval) -> str:
    lines: list[str] = []
    lines.append("## Forbidden Approval")
    lines.append("")
    lines.append(f"- **Category:** {forbidden.category}")
    lines.append(f"- **Description:** {forbidden.description}")
    lines.append(f"- **Requires Human Override:** {forbidden.requires_human_override}")
    lines.append("")
    return "\n".join(lines)


def render_approval_state_md(state: HumanReviewApprovalState) -> str:
    lines: list[str] = []
    lines.append("## Approval State")
    lines.append("")
    lines.append(f"- **State:** {state.state}")
    lines.append(f"- **Gate ID:** {state.gate_id}")
    lines.append(f"- **Approver:** {state.approver}")
    lines.append(f"- **Timestamp Slot:** {state.timestamp_slot}")
    lines.append("")
    if state.conditions:
        lines.append("### Conditions")
        for cond in state.conditions:
            lines.append(f"- {cond}")
        lines.append("")
    return "\n".join(lines)
