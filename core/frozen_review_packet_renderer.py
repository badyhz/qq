"""T1446 - Frozen review packet renderer.

Pure functions. No I/O. No network. No random. No timestamps. No env reads.
"""
from __future__ import annotations

from core.frozen_file_review_packet import FrozenFileReviewPacket
from core.frozen_review_check import FrozenReviewCheck
from core.frozen_file_risk_requirement import FrozenFileRiskRequirement
from core.frozen_risk_requirement_checklist import FrozenRiskRequirementChecklist


def render_review_packet_md(packet: FrozenFileReviewPacket) -> str:
    """Render FrozenFileReviewPacket to markdown."""
    lines: list[str] = []
    lines.append("## Frozen File Review Packet")
    lines.append("")
    lines.append(f"- **Packet ID:** {packet.packet_id}")
    lines.append(f"- **File Path:** {packet.file_path}")
    lines.append(f"- **Risk Class:** {packet.risk_class.value}")
    lines.append(f"- **File Category:** {packet.file_category}")
    lines.append(f"- **Decision Status:** {packet.decision_status.value}")
    lines.append("")
    if packet.review_checks:
        lines.append("### Review Checks")
        for check in packet.review_checks:
            lines.append(render_review_check_md(check))
    if packet.evidence_requirements:
        lines.append("### Evidence Requirements")
        for req in packet.evidence_requirements:
            lines.append(f"- {req}")
        lines.append("")
    return "\n".join(lines)


def render_review_check_md(check: FrozenReviewCheck) -> str:
    """Render FrozenReviewCheck to markdown."""
    return (
        f"- [{check.check_id}] {check.check_name} "
        f"({check.check_type.value}) = {check.status.value} — {check.description}"
    )


def render_risk_requirement_md(req: FrozenFileRiskRequirement) -> str:
    """Render FrozenFileRiskRequirement to markdown."""
    lines: list[str] = []
    lines.append(f"- **{req.requirement_id}** [{req.risk_class}] {req.requirement_name}")
    lines.append(f"  - mandatory={req.mandatory}, human_approval={req.human_approval_needed}")
    if req.required_evidence:
        lines.append(f"  - evidence: {', '.join(req.required_evidence)}")
    return "\n".join(lines)


def render_checklist_md(checklist: FrozenRiskRequirementChecklist) -> str:
    """Render FrozenRiskRequirementChecklist to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Risk Requirement Checklist")
    lines.append("")
    lines.append(f"- **Checklist ID:** {checklist.checklist_id}")
    lines.append(f"- **File Path:** {checklist.file_path}")
    lines.append(f"- **Risk Class:** {checklist.risk_class}")
    lines.append(f"- **Progress:** {checklist.completed_count}/{checklist.total_count}")
    lines.append(f"- **Complete:** {checklist.is_complete}")
    lines.append("")
    if checklist.requirements:
        lines.append("### Requirements")
        for req in checklist.requirements:
            lines.append(render_risk_requirement_md(req))
        lines.append("")
    return "\n".join(lines)
