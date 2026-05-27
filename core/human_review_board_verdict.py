"""T1386 - HumanReviewBoardVerdict frozen dataclass + build_verdict."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from core.human_review_board_packet import HumanReviewBoardPacket, PacketDecision
from core.human_review_evidence_check import EvidenceMatchStatus, HumanReviewEvidenceCheck
from core.human_review_item import HumanReviewItem, ReviewItemStatus
from core.human_review_risk_declaration import HumanReviewRiskDeclaration


class VerdictResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class HumanReviewBoardVerdict:
    verdict: VerdictResult
    notes: str
    missing_evidence: tuple[str, ...]
    unacknowledged_risks: tuple[str, ...]


def build_verdict(
    packet: HumanReviewBoardPacket,
    evidence_checks: tuple[HumanReviewEvidenceCheck, ...],
    risk_declarations: tuple[HumanReviewRiskDeclaration, ...],
) -> HumanReviewBoardVerdict:
    """Pure function: build a verdict from packet, evidence checks, and risk declarations."""
    notes_parts: list[str] = []

    # Collect missing evidence
    missing_evidence: list[str] = []
    for ec in evidence_checks:
        if ec.match_status != EvidenceMatchStatus.MATCH:
            missing_evidence.append(ec.check_id)
            notes_parts.append(f"evidence {ec.check_id}: {ec.match_status.value}")

    # Collect unacknowledged risks
    unacknowledged_risks: list[str] = []
    for rd in risk_declarations:
        if not rd.reviewer_acknowledgement:
            unacknowledged_risks.append(rd.declaration_id)
            notes_parts.append(f"risk {rd.declaration_id}: not acknowledged")

    # Check required items
    for item in packet.review_items:
        if item.required and item.status != ReviewItemStatus.VERIFIED:
            notes_parts.append(f"required item {item.item_id}: {item.status.value}")

    # Determine verdict
    if packet.decision == PacketDecision.REJECT:
        verdict = VerdictResult.FAIL
        notes_parts.insert(0, "packet decision is REJECT")
    elif missing_evidence or unacknowledged_risks:
        verdict = VerdictResult.INCOMPLETE
    elif all(
        item.status == ReviewItemStatus.VERIFIED
        for item in packet.review_items
        if item.required
    ):
        verdict = VerdictResult.PASS
    else:
        verdict = VerdictResult.INCOMPLETE

    notes = "; ".join(notes_parts) if notes_parts else "all checks passed"

    return HumanReviewBoardVerdict(
        verdict=verdict,
        notes=notes,
        missing_evidence=tuple(missing_evidence),
        unacknowledged_risks=tuple(unacknowledged_risks),
    )
