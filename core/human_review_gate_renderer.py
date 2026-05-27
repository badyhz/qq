"""T1121 - Human Review Gate Renderer."""
from __future__ import annotations

from core.human_review_gate import HumanReviewGate
from core.human_review_decision import HumanReviewDecision
from core.human_review_gate_verdict import HumanReviewGateVerdict


def render_human_review_gate_md(gate: HumanReviewGate) -> str:
    lines: list[str] = []
    lines.append("## Human Review Gate")
    lines.append("")
    lines.append(f"- **Gate ID:** {gate.gate_id}")
    lines.append(f"- **Gate Type:** {gate.gate_type}")
    lines.append(f"- **Status:** {gate.status}")
    lines.append("")
    if gate.required_evidence:
        lines.append("### Required Evidence")
        for item in gate.required_evidence:
            lines.append(f"- {item}")
        lines.append("")
    if gate.forbidden_approvals:
        lines.append("### Forbidden Approvals")
        for item in gate.forbidden_approvals:
            lines.append(f"- {item}")
        lines.append("")
    if gate.freeze_dependencies:
        lines.append("### Freeze Dependencies")
        for item in gate.freeze_dependencies:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def render_human_review_decision_md(decision: HumanReviewDecision) -> str:
    lines: list[str] = []
    lines.append("## Human Review Decision")
    lines.append("")
    lines.append("### Valid Decisions")
    lines.append(f"- APPROVE: {decision.APPROVE}")
    lines.append(f"- REJECT: {decision.REJECT}")
    lines.append(f"- ESCALATE: {decision.ESCALATE}")
    lines.append(f"- DEFER: {decision.DEFER}")
    lines.append(f"- CONDITIONAL_APPROVE: {decision.CONDITIONAL_APPROVE}")
    lines.append("")
    return "\n".join(lines)


def render_human_review_gate_verdict_md(verdict: HumanReviewGateVerdict) -> str:
    lines: list[str] = []
    lines.append("## Human Review Gate Verdict")
    lines.append("")
    lines.append(f"- **Gate ID:** {verdict.gate_id}")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    lines.append("")
    if verdict.issues:
        lines.append("### Issues")
        for issue in verdict.issues:
            lines.append(f"- {issue}")
        lines.append("")
    if verdict.notes:
        lines.append("### Notes")
        for note in verdict.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
