"""T1348 - Tests for human approval models."""
from __future__ import annotations

import pytest

from core.human_approval_evidence_pack import HumanApprovalEvidencePack
from core.human_approval_field_requirement import HumanApprovalFieldRequirement
from core.human_approval_reviewer import HumanApprovalReviewer
from core.human_approval_evidence_verdict import (
    HumanApprovalEvidenceVerdict,
    build_verdict,
)


class TestHumanApprovalEvidencePack:
    def test_create_pack(self):
        p = HumanApprovalEvidencePack("EP1", ("f1", "f2"), "reviewer1", "APPROVED")
        assert p.pack_id == "EP1"
        assert p.field_count() == 2
        assert p.has_field("f1")
        assert not p.has_field("f3")

    def test_immutable(self):
        p = HumanApprovalEvidencePack("EP2", (), "", "HOLD")
        with pytest.raises(AttributeError):
            p.verdict = "DENIED"  # type: ignore[misc]

    def test_to_dict(self):
        p = HumanApprovalEvidencePack("EP3", ("a",), "r", "APPROVED")
        d = p.to_dict()
        assert d["pack_id"] == "EP3"
        assert d["verdict"] == "APPROVED"


class TestHumanApprovalFieldRequirement:
    def test_create_requirement(self):
        r = HumanApprovalFieldRequirement(
            "FR1", "signature", "str", True, "non-empty"
        )
        assert r.field_id == "FR1"
        assert r.required is True

    def test_immutable(self):
        r = HumanApprovalFieldRequirement("FR2", "x", "str", False, "")
        with pytest.raises(AttributeError):
            r.required = True  # type: ignore[misc]

    def test_is_satisfied_by(self):
        r = HumanApprovalFieldRequirement("FR3", "x", "str", True, "")
        assert r.is_satisfied_by("str")
        assert not r.is_satisfied_by("int")


class TestHumanApprovalReviewer:
    def test_create_reviewer(self):
        r = HumanApprovalReviewer("RV1", "Alice", "admin", 5)
        assert r.reviewer_id == "RV1"
        assert r.name == "Alice"
        assert r.authority_level == 5

    def test_immutable(self):
        r = HumanApprovalReviewer("RV2", "Bob", "user", 1)
        with pytest.raises(AttributeError):
            r.authority_level = 10  # type: ignore[misc]

    def test_can_approve(self):
        r = HumanApprovalReviewer("RV3", "Carol", "admin", 5)
        assert r.can_approve(3)
        assert r.can_approve(5)
        assert not r.can_approve(6)


class TestHumanApprovalEvidenceVerdict:
    def test_build_approved(self):
        v = build_verdict("APPROVED", "looks good", (), "admin")
        assert v.is_approved()
        assert not v.has_missing_fields()

    def test_build_rejected(self):
        v = build_verdict("REJECTED", "missing proof", ("sig",), "reviewer")
        assert v.verdict == "REJECTED"
        assert v.has_missing_fields()

    def test_rejected_empty_notes_raises(self):
        with pytest.raises(ValueError, match="REJECTED.*notes"):
            build_verdict("REJECTED", "", (), "admin")

    def test_approved_with_missing_fields_raises(self):
        with pytest.raises(ValueError, match="APPROVED.*missing_fields"):
            build_verdict("APPROVED", "", ("f1",), "admin")

    def test_empty_approved_by_raises(self):
        with pytest.raises(ValueError, match="approved_by"):
            build_verdict("HOLD", "", (), "  ")

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValueError, match="verdict must be one of"):
            build_verdict("BOGUS", "", (), "admin")

    def test_immutable(self):
        v = build_verdict("HOLD", "waiting", (), "admin")
        with pytest.raises(AttributeError):
            v.notes = "changed"  # type: ignore[misc]
