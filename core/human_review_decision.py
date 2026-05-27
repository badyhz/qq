from __future__ import annotations


class HumanReviewDecision:
    APPROVE: str = "APPROVE"
    REJECT: str = "REJECT"
    ESCALATE: str = "ESCALATE"
    DEFER: str = "DEFER"
    CONDITIONAL_APPROVE: str = "CONDITIONAL_APPROVE"

    _VALID: frozenset[str] = frozenset({
        APPROVE,
        REJECT,
        ESCALATE,
        DEFER,
        CONDITIONAL_APPROVE,
    })

    def __init__(self) -> None:
        raise TypeError("HumanReviewDecision is not instantiable")


def validate_decision(decision: str) -> bool:
    return decision in HumanReviewDecision._VALID
