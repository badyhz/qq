from __future__ import annotations

import pytest

from core.human_review_board_packet import HumanReviewBoardPacket, PacketDecision
from core.human_review_item import HumanReviewItem, ReviewItemStatus
from core.human_review_decision_record import HumanReviewDecisionRecord
from core.human_review_evidence_check import HumanReviewEvidenceCheck, EvidenceMatchStatus
from core.human_review_risk_declaration import HumanReviewRiskDeclaration, RiskLevel
from core.human_review_board_verdict import HumanReviewBoardVerdict, VerdictResult, build_verdict


def _make_packet(decision: PacketDecision = PacketDecision.PENDING, items: tuple = ()) -> HumanReviewBoardPacket:
    return HumanReviewBoardPacket(
        packet_id="P-001",
        target_file="core/live_runner.py",
        risk_class="HIGH",
        review_items=items,
        decision=decision,
        reviewer="human-001",
    )


def _make_evidence(check_id: str = "E-001", match: EvidenceMatchStatus = EvidenceMatchStatus.MATCH) -> HumanReviewEvidenceCheck:
    return HumanReviewEvidenceCheck(
        check_id=check_id,
        evidence_type="dry_run_proof",
        expected="PASS",
        actual="PASS",
        match_status=match,
    )


def _make_risk(decl_id: str = "R-001", acknowledged: bool = True) -> HumanReviewRiskDeclaration:
    return HumanReviewRiskDeclaration(
        declaration_id=decl_id,
        risk_level=RiskLevel.HIGH,
        acknowledged_risks=("live_trading",),
        mitigation_plan="rollback",
        reviewer_acknowledgement=acknowledged,
    )


class TestHumanReviewBoardPacket:
    def test_create_packet(self) -> None:
        packet = _make_packet()
        assert packet.packet_id == "P-001"

    def test_immutable(self) -> None:
        packet = _make_packet()
        with pytest.raises(AttributeError):
            packet.packet_id = "X"  # type: ignore[misc]

    def test_with_review_items(self) -> None:
        item = HumanReviewItem(
            item_id="I-001",
            category="evidence",
            description="Dry run proof",
            required=True,
            status="PENDING",
        )
        packet = _make_packet(items=(item,))
        assert len(packet.review_items) == 1


class TestHumanReviewItem:
    def test_create_item(self) -> None:
        item = HumanReviewItem(
            item_id="I-001", category="evidence", description="Dry run proof",
            required=True, status="PENDING",
        )
        assert item.category == "evidence"

    def test_immutable(self) -> None:
        item = HumanReviewItem(
            item_id="I-001", category="evidence", description="test",
            required=True, status="PENDING",
        )
        with pytest.raises(AttributeError):
            item.item_id = "X"  # type: ignore[misc]


class TestHumanReviewDecisionRecord:
    def test_create_record(self) -> None:
        record = HumanReviewDecisionRecord(
            record_id="D-001", decision="APPROVE", rationale="All checks passed",
            conditions=("dry_run_verified",), reviewer_id="human-001",
        )
        assert record.decision == "APPROVE"
        assert len(record.conditions) == 1

    def test_immutable(self) -> None:
        record = HumanReviewDecisionRecord(
            record_id="D-001", decision="APPROVE", rationale="test",
            conditions=(), reviewer_id="human-001",
        )
        with pytest.raises(AttributeError):
            record.decision = "X"  # type: ignore[misc]


class TestHumanReviewEvidenceCheck:
    def test_create_check(self) -> None:
        check = _make_evidence()
        assert check.match_status == EvidenceMatchStatus.MATCH


class TestHumanReviewRiskDeclaration:
    def test_create_declaration(self) -> None:
        decl = _make_risk()
        assert decl.risk_level == RiskLevel.HIGH
        assert len(decl.acknowledged_risks) == 1

    def test_not_acknowledged(self) -> None:
        decl = _make_risk(acknowledged=False)
        assert decl.reviewer_acknowledgement is False


class TestHumanReviewBoardVerdict:
    def test_build_verdict_pass(self) -> None:
        packet = _make_packet()
        verdict = build_verdict(
            packet=packet,
            evidence_checks=(_make_evidence(),),
            risk_declarations=(_make_risk(),),
        )
        assert verdict.verdict == VerdictResult.PASS

    def test_build_verdict_incomplete_missing_evidence(self) -> None:
        packet = _make_packet()
        verdict = build_verdict(
            packet=packet,
            evidence_checks=(_make_evidence(match=EvidenceMatchStatus.MISMATCH),),
            risk_declarations=(_make_risk(),),
        )
        assert verdict.verdict == VerdictResult.INCOMPLETE
        assert len(verdict.missing_evidence) == 1

    def test_build_verdict_incomplete_unacknowledged_risk(self) -> None:
        packet = _make_packet()
        verdict = build_verdict(
            packet=packet,
            evidence_checks=(_make_evidence(),),
            risk_declarations=(_make_risk(acknowledged=False),),
        )
        assert verdict.verdict == VerdictResult.INCOMPLETE
        assert len(verdict.unacknowledged_risks) == 1

    def test_build_verdict_fail_on_reject(self) -> None:
        packet = _make_packet(decision=PacketDecision.REJECT)
        verdict = build_verdict(
            packet=packet,
            evidence_checks=(_make_evidence(),),
            risk_declarations=(_make_risk(),),
        )
        assert verdict.verdict == VerdictResult.FAIL

    def test_verdict_immutable(self) -> None:
        packet = _make_packet()
        verdict = build_verdict(
            packet=packet,
            evidence_checks=(_make_evidence(),),
            risk_declarations=(_make_risk(),),
        )
        with pytest.raises(AttributeError):
            verdict.verdict = "X"  # type: ignore[misc]
