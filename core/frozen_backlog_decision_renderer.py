"""T1378 - Frozen Backlog Decision Renderer."""
from __future__ import annotations

from core.frozen_backlog_decision_matrix import FrozenBacklogDecisionMatrix
from core.frozen_backlog_decision_item import FrozenBacklogDecisionItem
from core.frozen_backlog_action_policy import FrozenBacklogActionPolicy
from core.frozen_backlog_risk_assessment import FrozenBacklogRiskAssessment
from core.frozen_backlog_matrix_verdict import FrozenBacklogMatrixVerdict


def render_decision_matrix_md(matrix: FrozenBacklogDecisionMatrix) -> str:
    """Render FrozenBacklogDecisionMatrix to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Decision Matrix")
    lines.append("")
    lines.append(f"- **Matrix ID:** {matrix.matrix_id}")
    lines.append(f"- **Item Count:** {len(matrix.items)}")
    lines.append(f"- **Policy Count:** {len(matrix.policies)}")
    lines.append("")
    if matrix.items:
        lines.append("### Decision Items")
        for item in matrix.items:
            lines.append(f"- [{item.item_id}] {item.file_path} risk={item.risk_class} state={item.current_state}")
        lines.append("")
    if matrix.policies:
        lines.append("### Action Policies")
        for policy in matrix.policies:
            lines.append(f"- [{policy.policy_id}] {policy.action_name} blocked={policy.blocked}")
        lines.append("")
    if matrix.verdict:
        lines.append(render_matrix_verdict_md(matrix.verdict))
    return "\n".join(lines)


def render_decision_item_md(item: FrozenBacklogDecisionItem) -> str:
    """Render FrozenBacklogDecisionItem to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Decision Item")
    lines.append("")
    lines.append(f"- **Item ID:** {item.item_id}")
    lines.append(f"- **File Path:** {item.file_path}")
    lines.append(f"- **Risk Class:** {item.risk_class}")
    lines.append(f"- **Current State:** {item.current_state}")
    lines.append("")
    if item.allowed_actions:
        lines.append("### Allowed Actions")
        for action in item.allowed_actions:
            lines.append(f"- {action}")
        lines.append("")
    if item.forbidden_actions:
        lines.append("### Forbidden Actions")
        for action in item.forbidden_actions:
            lines.append(f"- {action}")
        lines.append("")
    if item.required_evidence:
        lines.append("### Required Evidence")
        for evidence in item.required_evidence:
            lines.append(f"- {evidence}")
        lines.append("")
    return "\n".join(lines)


def render_action_policy_md(policy: FrozenBacklogActionPolicy) -> str:
    """Render FrozenBacklogActionPolicy to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Action Policy")
    lines.append("")
    lines.append(f"- **Policy ID:** {policy.policy_id}")
    lines.append(f"- **Action Name:** {policy.action_name}")
    lines.append(f"- **Requires Human Approval:** {policy.requires_human_approval}")
    lines.append(f"- **Blocked:** {policy.blocked}")
    lines.append("")
    if policy.allowed_for_risk:
        lines.append("### Allowed For Risk Classes")
        for risk in policy.allowed_for_risk:
            lines.append(f"- {risk}")
        lines.append("")
    return "\n".join(lines)


def render_risk_assessment_md(assessment: FrozenBacklogRiskAssessment) -> str:
    """Render FrozenBacklogRiskAssessment to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Risk Assessment")
    lines.append("")
    lines.append(f"- **Assessment ID:** {assessment.assessment_id}")
    lines.append(f"- **File Path:** {assessment.file_path}")
    lines.append(f"- **Risk Score:** {assessment.risk_score}")
    lines.append("")
    if assessment.risk_factors:
        lines.append("### Risk Factors")
        for factor in assessment.risk_factors:
            lines.append(f"- {factor}")
        lines.append("")
    if assessment.mitigation_steps:
        lines.append("### Mitigation Steps")
        for step in assessment.mitigation_steps:
            lines.append(f"- {step}")
        lines.append("")
    return "\n".join(lines)


def render_matrix_verdict_md(verdict: FrozenBacklogMatrixVerdict) -> str:
    """Render FrozenBacklogMatrixVerdict to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Matrix Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    if verdict.notes:
        lines.append(f"- **Notes:** {verdict.notes}")
    lines.append("")
    if verdict.blocked_items:
        lines.append("### Blocked Items")
        for item_id in verdict.blocked_items:
            lines.append(f"- {item_id}")
        lines.append("")
    if verdict.promotable_items:
        lines.append("### Promotable Items")
        for item_id in verdict.promotable_items:
            lines.append(f"- {item_id}")
        lines.append("")
    return "\n".join(lines)
