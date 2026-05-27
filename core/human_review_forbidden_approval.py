from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReviewForbiddenApproval:
    category: str
    description: str
    requires_human_override: bool


VALID_CATEGORIES: frozenset[str] = frozenset({
    "LIVE_TRADING",
    "CREDENTIAL_ACCESS",
    "EXCHANGE_CONNECTION",
    "PLANNER_INTEGRATION",
})


def build_forbidden_approval(
    category: str,
    description: str,
    requires_human_override: bool = True,
) -> HumanReviewForbiddenApproval:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category}. Must be one of {VALID_CATEGORIES}")
    return HumanReviewForbiddenApproval(
        category=category,
        description=description,
        requires_human_override=requires_human_override,
    )
