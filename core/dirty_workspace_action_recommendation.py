from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirtyWorkspaceActionRecommendation:
    KEEP_UNCOMMITTED: str = "KEEP_UNCOMMITTED"
    REVIEW: str = "REVIEW"
    STASH: str = "STASH"
    COMMIT_LATER: str = "COMMIT_LATER"
    DELETE_WITH_HUMAN_CONFIRMATION: str = "DELETE_WITH_HUMAN_CONFIRMATION"
    HUMAN_REVIEW_ONLY: str = "HUMAN_REVIEW_ONLY"

    ALL_VALUES: tuple[str, ...] = (
        "KEEP_UNCOMMITTED",
        "REVIEW",
        "STASH",
        "COMMIT_LATER",
        "DELETE_WITH_HUMAN_CONFIRMATION",
        "HUMAN_REVIEW_ONLY",
    )


def validate_action(value: str) -> bool:
    return value in DirtyWorkspaceActionRecommendation.ALL_VALUES
