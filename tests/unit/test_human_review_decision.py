from __future__ import annotations

import pytest

from core.human_review_decision import (
    HumanReviewDecision,
    validate_decision,
)


class TestHumanReviewDecision:
    def test_not_instantiable(self) -> None:
        with pytest.raises(TypeError):
            HumanReviewDecision()

    def test_approve_value(self) -> None:
        assert HumanReviewDecision.APPROVE == "APPROVE"

    def test_reject_value(self) -> None:
        assert HumanReviewDecision.REJECT == "REJECT"

    def test_escalate_value(self) -> None:
        assert HumanReviewDecision.ESCALATE == "ESCALATE"

    def test_defer_value(self) -> None:
        assert HumanReviewDecision.DEFER == "DEFER"

    def test_conditional_approve_value(self) -> None:
        assert HumanReviewDecision.CONDITIONAL_APPROVE == "CONDITIONAL_APPROVE"

    def test_validate_valid_decisions(self) -> None:
        for d in (
            HumanReviewDecision.APPROVE,
            HumanReviewDecision.REJECT,
            HumanReviewDecision.ESCALATE,
            HumanReviewDecision.DEFER,
            HumanReviewDecision.CONDITIONAL_APPROVE,
        ):
            assert validate_decision(d) is True

    def test_validate_invalid_decision(self) -> None:
        assert validate_decision("INVALID") is False
        assert validate_decision("") is False
        assert validate_decision("approve") is False
