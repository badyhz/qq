from __future__ import annotations

import pytest

from core.human_review_evidence_checklist import (
    EvidenceItem,
    HumanReviewEvidenceChecklist,
    build_evidence_checklist,
    build_evidence_item,
    all_required_verified,
)


class TestHumanReviewEvidenceChecklist:
    def test_build_item(self) -> None:
        item = build_evidence_item(name="doc.pdf", required=True, verified=False)
        assert item.name == "doc.pdf"
        assert item.required is True
        assert item.verified is False

    def test_item_frozen(self) -> None:
        item = build_evidence_item(name="x")
        with pytest.raises(AttributeError):
            item.name = "y"  # type: ignore[misc]

    def test_build_checklist(self) -> None:
        items = (
            build_evidence_item("a", required=True, verified=True),
            build_evidence_item("b", required=False, verified=False),
        )
        cl = build_evidence_checklist(gate_id="G1", items=items)
        assert cl.gate_id == "G1"
        assert len(cl.items) == 2

    def test_checklist_frozen(self) -> None:
        cl = build_evidence_checklist(gate_id="G2")
        with pytest.raises(AttributeError):
            cl.gate_id = "X"  # type: ignore[misc]

    def test_all_required_verified_true(self) -> None:
        items = (
            build_evidence_item("a", required=True, verified=True),
            build_evidence_item("b", required=False, verified=False),
        )
        cl = build_evidence_checklist(gate_id="G", items=items)
        assert all_required_verified(cl) is True

    def test_all_required_verified_false(self) -> None:
        items = (
            build_evidence_item("a", required=True, verified=False),
        )
        cl = build_evidence_checklist(gate_id="G", items=items)
        assert all_required_verified(cl) is False

    def test_empty_checklist(self) -> None:
        cl = build_evidence_checklist(gate_id="G")
        assert all_required_verified(cl) is True
