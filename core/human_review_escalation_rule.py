from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReviewEscalationRule:
    level: str
    trigger_condition: str
    required_evidence: tuple[str, ...]
    target_role: str


VALID_LEVELS: frozenset[str] = frozenset({
    "L1_AGENT",
    "L2_OPERATOR",
    "L3_ADMIN",
    "L4_EMERGENCY",
})


def build_escalation_rule(
    level: str,
    trigger_condition: str,
    required_evidence: tuple[str, ...] = (),
    target_role: str = "",
) -> HumanReviewEscalationRule:
    if level not in VALID_LEVELS:
        raise ValueError(f"Invalid level: {level}. Must be one of {VALID_LEVELS}")
    return HumanReviewEscalationRule(
        level=level,
        trigger_condition=trigger_condition,
        required_evidence=tuple(required_evidence),
        target_role=target_role,
    )
