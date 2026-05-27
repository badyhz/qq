from __future__ import annotations

from core.human_review_board_packet import HumanReviewBoardPacket
from core.human_review_item import HumanReviewItem
from core.human_review_decision_record import HumanReviewDecisionRecord
from core.human_review_evidence_check import HumanReviewEvidenceCheck
from core.human_review_risk_declaration import HumanReviewRiskDeclaration
from core.human_review_board_verdict import HumanReviewBoardVerdict


def render_review_board_packet_md(packet: HumanReviewBoardPacket) -> str:
    lines = ("# Human Review Board Packet", "")
    lines += (f"- **Packet ID:** {packet.packet_id}",)
    lines += (f"- **Target file:** {packet.target_file}",)
    lines += (f"- **Risk class:** {packet.risk_class}",)
    lines += (f"- **Decision:** {packet.decision}",)
    lines += (f"- **Reviewer:** {packet.reviewer}",)
    if packet.review_items:
        lines += ("", "## Review Items",)
        for item in packet.review_items:
            lines += (f"- [{item.status}] {item.category}: {item.description}",)
    return "\n".join(lines)


def render_review_item_md(item: HumanReviewItem) -> str:
    lines = ("# Human Review Item", "")
    lines += (f"- **Item ID:** {item.item_id}",)
    lines += (f"- **Category:** {item.category}",)
    lines += (f"- **Description:** {item.description}",)
    lines += (f"- **Required:** {item.required}",)
    lines += (f"- **Status:** {item.status}",)
    return "\n".join(lines)


def render_decision_record_md(record: HumanReviewDecisionRecord) -> str:
    lines = ("# Human Review Decision Record", "")
    lines += (f"- **Record ID:** {record.record_id}",)
    lines += (f"- **Decision:** {record.decision}",)
    lines += (f"- **Rationale:** {record.rationale}",)
    lines += (f"- **Reviewer:** {record.reviewer_id}",)
    if record.conditions:
        lines += ("", "## Conditions",)
        for c in record.conditions:
            lines += (f"- {c}",)
    return "\n".join(lines)


def render_evidence_check_md(check: HumanReviewEvidenceCheck) -> str:
    lines = ("# Human Review Evidence Check", "")
    lines += (f"- **Check ID:** {check.check_id}",)
    lines += (f"- **Evidence type:** {check.evidence_type}",)
    lines += (f"- **Expected:** {check.expected}",)
    lines += (f"- **Actual:** {check.actual}",)
    lines += (f"- **Match status:** {check.match_status}",)
    return "\n".join(lines)


def render_risk_declaration_md(decl: HumanReviewRiskDeclaration) -> str:
    lines = ("# Human Review Risk Declaration", "")
    lines += (f"- **Declaration ID:** {decl.declaration_id}",)
    lines += (f"- **Risk level:** {decl.risk_level}",)
    lines += (f"- **Mitigation plan:** {decl.mitigation_plan}",)
    lines += (f"- **Reviewer acknowledgement:** {decl.reviewer_acknowledgement}",)
    if decl.acknowledged_risks:
        lines += ("", "## Acknowledged Risks",)
        for r in decl.acknowledged_risks:
            lines += (f"- {r}",)
    return "\n".join(lines)


def render_board_verdict_md(verdict: HumanReviewBoardVerdict) -> str:
    lines = ("# Human Review Board Verdict", "")
    lines += (f"- **Verdict:** {verdict.verdict}",)
    lines += (f"- **Notes:** {verdict.notes}",)
    if verdict.missing_evidence:
        lines += ("", "## Missing Evidence",)
        for m in verdict.missing_evidence:
            lines += (f"- {m}",)
    if verdict.unacknowledged_risks:
        lines += ("", "## Unacknowledged Risks",)
        for u in verdict.unacknowledged_risks:
            lines += (f"- {u}",)
    return "\n".join(lines)
