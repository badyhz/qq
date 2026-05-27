"""T1379 - Tests for frozen backlog decision matrix models."""
from __future__ import annotations

import pytest


class TestFrozenBacklogDecisionItem:
    """Tests for FrozenBacklogDecisionItem."""

    def test_create_decision_item_frozen(self):
        from core.frozen_backlog_decision_item import build_decision_item

        item = build_decision_item(
            item_id="I-001",
            file_path="core/foo.py",
            risk_class="HIGH",
            allowed_actions=("review", "freeze"),
            forbidden_actions=("delete",),
            required_evidence=("test_pass",),
            current_state="pending",
        )
        assert item.item_id == "I-001"
        assert item.risk_class == "HIGH"

    def test_decision_item_immutability(self):
        from core.frozen_backlog_decision_item import build_decision_item

        item = build_decision_item(item_id="I-002", file_path="core/bar.py", risk_class="MEDIUM")
        with pytest.raises(AttributeError):
            item.item_id = "changed"  # type: ignore[misc]

    def test_decision_item_invalid_risk_class(self):
        from core.frozen_backlog_decision_item import build_decision_item

        with pytest.raises(ValueError, match="Invalid risk_class"):
            build_decision_item(item_id="I-003", file_path="core/baz.py", risk_class="LOW")

    def test_decision_item_to_dict(self):
        from core.frozen_backlog_decision_item import build_decision_item

        item = build_decision_item(item_id="I-004", file_path="core/x.py", risk_class="HIGH")
        d = item.to_dict()
        assert d["item_id"] == "I-004"
        assert d["risk_class"] == "HIGH"


class TestFrozenBacklogActionPolicy:
    """Tests for FrozenBacklogActionPolicy."""

    def test_create_action_policy_frozen(self):
        from core.frozen_backlog_action_policy import build_action_policy

        policy = build_action_policy(
            policy_id="P-001",
            action_name="freeze",
            allowed_for_risk=("HIGH", "MEDIUM"),
            requires_human_approval=True,
            blocked=False,
        )
        assert policy.policy_id == "P-001"
        assert policy.blocked is False

    def test_action_policy_immutability(self):
        from core.frozen_backlog_action_policy import build_action_policy

        policy = build_action_policy(policy_id="P-002", action_name="review")
        with pytest.raises(AttributeError):
            policy.blocked = True  # type: ignore[misc]


class TestFrozenBacklogRiskAssessment:
    """Tests for FrozenBacklogRiskAssessment."""

    def test_create_risk_assessment_frozen(self):
        from core.frozen_backlog_risk_assessment import build_risk_assessment

        assessment = build_risk_assessment(
            assessment_id="RA-001",
            file_path="core/x.py",
            risk_factors=("no_tests", "recent_changes"),
            risk_score=0.75,
            mitigation_steps=("add tests", "peer_review"),
        )
        assert assessment.risk_score == 0.75
        assert len(assessment.risk_factors) == 2

    def test_risk_assessment_immutability(self):
        from core.frozen_backlog_risk_assessment import build_risk_assessment

        assessment = build_risk_assessment(assessment_id="RA-002", file_path="core/y.py")
        with pytest.raises(AttributeError):
            assessment.risk_score = 1.0  # type: ignore[misc]


class TestFrozenBacklogMatrixVerdict:
    """Tests for FrozenBacklogMatrixVerdict and build_verdict."""

    def test_build_verdict_valid(self):
        from core.frozen_backlog_matrix_verdict import build_verdict

        v = build_verdict(verdict="HOLD", notes="waiting", blocked_items=("I-001",), promotable_items=("I-002",))
        assert v.verdict == "HOLD"
        assert v.blocked_items == ("I-001",)
        assert v.promotable_items == ("I-002",)

    def test_build_verdict_invalid(self):
        from core.frozen_backlog_matrix_verdict import build_verdict

        with pytest.raises(ValueError, match="Invalid verdict"):
            build_verdict(verdict="INVALID")

    def test_verdict_immutability(self):
        from core.frozen_backlog_matrix_verdict import build_verdict

        v = build_verdict(verdict="PASS")
        with pytest.raises(AttributeError):
            v.verdict = "BLOCKED"  # type: ignore[misc]

    def test_verdict_to_dict(self):
        from core.frozen_backlog_matrix_verdict import build_verdict

        v = build_verdict(verdict="BLOCKED", notes="test", blocked_items=("X",))
        d = v.to_dict()
        assert d["verdict"] == "BLOCKED"
        assert d["blocked_items"] == ("X",)


class TestFrozenBacklogDecisionMatrix:
    """Tests for FrozenBacklogDecisionMatrix."""

    def test_create_matrix_frozen(self):
        from core.frozen_backlog_decision_matrix import build_decision_matrix
        from core.frozen_backlog_decision_item import build_decision_item
        from core.frozen_backlog_action_policy import build_action_policy
        from core.frozen_backlog_matrix_verdict import build_verdict

        item = build_decision_item(item_id="I-001", file_path="core/x.py", risk_class="HIGH")
        policy = build_action_policy(policy_id="P-001", action_name="freeze")
        verdict = build_verdict(verdict="HOLD")

        matrix = build_decision_matrix(
            matrix_id="M-001",
            items=(item,),
            policies=(policy,),
            verdict=verdict,
        )
        assert matrix.matrix_id == "M-001"
        assert len(matrix.items) == 1
        assert len(matrix.policies) == 1
        assert matrix.verdict is not None

    def test_matrix_immutability(self):
        from core.frozen_backlog_decision_matrix import build_decision_matrix

        matrix = build_decision_matrix(matrix_id="M-002")
        with pytest.raises(AttributeError):
            matrix.matrix_id = "changed"  # type: ignore[misc]

    def test_matrix_to_dict(self):
        from core.frozen_backlog_decision_matrix import build_decision_matrix

        matrix = build_decision_matrix(matrix_id="M-003")
        d = matrix.to_dict()
        assert d["matrix_id"] == "M-003"
        assert d["items"] == []
        assert d["verdict"] is None


class TestFrozenBacklogEvidenceSpec:
    """Tests for FrozenBacklogEvidenceSpec."""

    def test_create_evidence_spec_frozen(self):
        from core.frozen_backlog_evidence_spec import build_evidence_spec

        spec = build_evidence_spec(
            spec_id="ES-001",
            evidence_type="test_output",
            required_fields=("pass_rate", "duration"),
            format="json",
            mandatory=True,
        )
        assert spec.spec_id == "ES-001"
        assert spec.mandatory is True

    def test_evidence_spec_immutability(self):
        from core.frozen_backlog_evidence_spec import build_evidence_spec

        spec = build_evidence_spec(spec_id="ES-002", evidence_type="log")
        with pytest.raises(AttributeError):
            spec.mandatory = False  # type: ignore[misc]


class TestFrozenBacklogPromotionGate:
    """Tests for FrozenBacklogPromotionGate."""

    def test_create_promotion_gate_frozen(self):
        from core.frozen_backlog_promotion_gate import build_promotion_gate

        gate = build_promotion_gate(
            gate_id="G-001",
            from_state="pending",
            to_state="approved",
            prerequisites=("tests_pass",),
            blockers=("no_evidence",),
            requires_human=True,
        )
        assert gate.gate_id == "G-001"
        assert gate.requires_human is True

    def test_promotion_gate_immutability(self):
        from core.frozen_backlog_promotion_gate import build_promotion_gate

        gate = build_promotion_gate(gate_id="G-002", from_state="a", to_state="b")
        with pytest.raises(AttributeError):
            gate.requires_human = True  # type: ignore[misc]
