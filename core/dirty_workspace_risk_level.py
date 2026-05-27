from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirtyWorkspaceRiskLevel:
    LOW: str = "LOW"
    MEDIUM: str = "MEDIUM"
    HIGH: str = "HIGH"
    CRITICAL: str = "CRITICAL"

    ALL_VALUES: tuple[str, ...] = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


_RISK_LEVEL_TO_ACTION: dict[str, str] = {
    "LOW": "COMMIT_LATER",
    "MEDIUM": "REVIEW",
    "HIGH": "HUMAN_REVIEW_ONLY",
    "CRITICAL": "KEEP_UNCOMMITTED",
}


def risk_level_to_action(risk_level: str) -> str:
    """Map a risk level to its default action recommendation string."""
    return _RISK_LEVEL_TO_ACTION.get(risk_level, "HUMAN_REVIEW_ONLY")
