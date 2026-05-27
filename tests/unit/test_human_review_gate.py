from __future__ import annotations

import pytest

from core.human_review_gate import (
    HumanReviewGate,
    build_gate,
    gate_to_dict,
)


class TestHumanReviewGate:
    def test_build_gate_valid(self) -> None:
        g = build_gate(gate_id="G1", gate_type="RELEASE")
        assert g.gate_id == "G1"
        assert g.gate_type == "RELEASE"
        assert g.status == "PENDING_APPROVAL"

    def test_frozen(self) -> None:
        g = build_gate(gate_id="G2", gate_type="REVIEW")
        with pytest.raises(AttributeError):
            g.gate_id = "X"  # type: ignore[misc]

    def test_gate_type_values(self) -> None:
        for gt in ("RELEASE", "REVIEW", "HOTFIX", "DEPLOYMENT"):
            g = build_gate(gate_id="G", gate_type=gt)
            assert g.gate_type == gt

    def test_status_values(self) -> None:
        for st in ("PENDING_APPROVAL", "APPROVED", "REJECTED", "ESCALATED"):
            g = build_gate(gate_id="G", gate_type="R", status=st)
            assert g.status == st

    def test_gate_to_dict_keys(self) -> None:
        g = build_gate(
            gate_id="G3",
            gate_type="RELEASE",
            required_evidence=("doc",),
            forbidden_approvals=("LIVE_TRADING",),
            freeze_dependencies=("f1",),
        )
        d = gate_to_dict(g)
        assert set(d.keys()) == {
            "gate_id",
            "gate_type",
            "status",
            "required_evidence",
            "forbidden_approvals",
            "freeze_dependencies",
        }
        assert d["required_evidence"] == ["doc"]

    def test_empty_tuples_default(self) -> None:
        g = build_gate(gate_id="G4", gate_type="T")
        assert g.required_evidence == ()
        assert g.forbidden_approvals == ()
        assert g.freeze_dependencies == ()
