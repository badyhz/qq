"""T1123 - Human Review Evidence Packet Renderer."""
from __future__ import annotations

from core.human_review_evidence_checklist import HumanReviewEvidenceChecklist
from core.human_review_approval_state import HumanReviewApprovalState
from core.human_review_rejection_state import HumanReviewRejectionState
from core.human_review_rollback_requirement import HumanReviewRollbackRequirement
from core.human_review_escalation_rule import HumanReviewEscalationRule


def render_evidence_packet_md(
    checklist: HumanReviewEvidenceChecklist,
    approval_state: HumanReviewApprovalState,
    rejection_state: HumanReviewRejectionState,
) -> str:
    lines: list[str] = []
    lines.append("## Evidence Packet")
    lines.append("")
    lines.append(f"### Checklist (Gate: {checklist.gate_id})")
    lines.append(f"- Items: {len(checklist.items)}")
    verified = sum(1 for i in checklist.items if i.verified)
    required = sum(1 for i in checklist.items if i.required)
    lines.append(f"- Verified: {verified}/{len(checklist.items)}")
    lines.append(f"- Required: {required}")
    lines.append("")
    lines.append(f"### Approval State")
    lines.append(f"- State: {approval_state.state}")
    lines.append(f"- Approver: {approval_state.approver}")
    lines.append(f"- Slot: {approval_state.timestamp_slot}")
    if approval_state.conditions:
        lines.append("- Conditions:")
        for c in approval_state.conditions:
            lines.append(f"  - {c}")
    lines.append("")
    lines.append(f"### Rejection State")
    lines.append(f"- State: {rejection_state.state}")
    lines.append(f"- Rejector: {rejection_state.rejector}")
    lines.append(f"- Reason: {rejection_state.reason}")
    lines.append(f"- Revision Allowed: {rejection_state.revision_allowed}")
    lines.append("")
    return "\n".join(lines)


def render_rollback_requirement_md(req: HumanReviewRollbackRequirement) -> str:
    lines: list[str] = []
    lines.append("## Rollback Requirement")
    lines.append("")
    lines.append(f"- **Gate ID:** {req.gate_id}")
    lines.append(f"- **Verification Command:** `{req.verification_command}`")
    lines.append(f"- **Expected Outcome:** {req.expected_outcome}")
    lines.append("")
    if req.rollback_steps:
        lines.append("### Rollback Steps")
        for idx, step in enumerate(req.rollback_steps, 1):
            lines.append(f"{idx}. {step}")
        lines.append("")
    return "\n".join(lines)


def render_escalation_rule_md(rule: HumanReviewEscalationRule) -> str:
    lines: list[str] = []
    lines.append("## Escalation Rule")
    lines.append("")
    lines.append(f"- **Level:** {rule.level}")
    lines.append(f"- **Trigger Condition:** {rule.trigger_condition}")
    lines.append(f"- **Target Role:** {rule.target_role}")
    lines.append("")
    if rule.required_evidence:
        lines.append("### Required Evidence")
        for item in rule.required_evidence:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)
