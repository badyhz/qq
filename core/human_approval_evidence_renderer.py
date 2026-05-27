"""T1344 - Human Approval Evidence Renderer."""
from __future__ import annotations

from core.human_approval_evidence_pack import HumanApprovalEvidencePack
from core.human_approval_field_requirement import HumanApprovalFieldRequirement
from core.human_approval_reviewer import HumanApprovalReviewer
from core.human_approval_evidence_verdict import HumanApprovalEvidenceVerdict


def render_human_approval_evidence_pack_md(pack: HumanApprovalEvidencePack) -> str:
    """Render HumanApprovalEvidencePack to markdown."""
    lines: list[str] = []
    lines.append("## Human Approval Evidence Pack")
    lines.append("")
    lines.append(f"- **Pack ID:** {pack.pack_id}")
    lines.append(f"- **Reviewer:** {pack.reviewer}")
    lines.append(f"- **Verdict:** {pack.verdict}")
    lines.append(f"- **Field Count:** {pack.field_count()}")
    lines.append("")
    if pack.fields:
        lines.append("### Fields")
        for field in pack.fields:
            lines.append(f"- {field}")
        lines.append("")
    return "\n".join(lines)


def render_human_approval_field_requirement_md(req: HumanApprovalFieldRequirement) -> str:
    """Render HumanApprovalFieldRequirement to markdown."""
    lines: list[str] = []
    lines.append("## Human Approval Field Requirement")
    lines.append("")
    lines.append(f"- **Field ID:** {req.field_id}")
    lines.append(f"- **Field Name:** {req.field_name}")
    lines.append(f"- **Field Type:** {req.field_type}")
    lines.append(f"- **Required:** {req.required}")
    lines.append(f"- **Validation Rule:** {req.validation_rule}")
    lines.append("")
    return "\n".join(lines)


def render_human_approval_reviewer_md(reviewer: HumanApprovalReviewer) -> str:
    """Render HumanApprovalReviewer to markdown."""
    lines: list[str] = []
    lines.append("## Human Approval Reviewer")
    lines.append("")
    lines.append(f"- **Reviewer ID:** {reviewer.reviewer_id}")
    lines.append(f"- **Name:** {reviewer.name}")
    lines.append(f"- **Role:** {reviewer.role}")
    lines.append(f"- **Authority Level:** {reviewer.authority_level}")
    lines.append("")
    return "\n".join(lines)


def render_human_approval_verdict_md(verdict: HumanApprovalEvidenceVerdict) -> str:
    """Render HumanApprovalEvidenceVerdict to markdown."""
    lines: list[str] = []
    lines.append("## Human Approval Evidence Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    lines.append(f"- **Approved By:** {verdict.approved_by}")
    lines.append(f"- **Missing Fields Count:** {len(verdict.missing_fields)}")
    if verdict.notes:
        lines.append(f"- **Notes:** {verdict.notes}")
    lines.append("")
    if verdict.missing_fields:
        lines.append("### Missing Fields")
        for field in verdict.missing_fields:
            lines.append(f"- {field}")
        lines.append("")
    return "\n".join(lines)
