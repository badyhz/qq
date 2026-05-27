"""T1522 - Frozen Backlog Inventory Record."""
from __future__ import annotations

from dataclasses import dataclass

VALID_RISK_CLASSES: tuple[str, ...] = ("HIGH", "MEDIUM")
VALID_CATEGORIES: tuple[str, ...] = (
    "LIVE_RUNNER",
    "LIVE_PLAYBOOK",
    "SUBMIT",
    "TESTNET_SMOKE",
    "FLATTEN",
    "REPLAY_SUBMIT",
    "OPERATIONAL_SHADOW",
    "VERIFICATION",
)
VALID_UNLOCK_RECOMMENDATIONS: tuple[str, ...] = ("HOLD", "PROMOTE", "DEFER", "REJECT")


@dataclass(frozen=True)
class FrozenBacklogInventoryRecord:
    """Immutable inventory record for a single frozen backlog file.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    file_path: str
    risk_class: str
    category: str
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    promotion_readiness_default: float
    unlock_recommendation: str
    release_hold: str

    def __post_init__(self) -> None:
        if self.risk_class not in VALID_RISK_CLASSES:
            raise ValueError(
                f"Invalid risk_class {self.risk_class!r}; "
                f"must be one of {VALID_RISK_CLASSES}"
            )
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category {self.category!r}; "
                f"must be one of {VALID_CATEGORIES}"
            )
        if self.unlock_recommendation not in VALID_UNLOCK_RECOMMENDATIONS:
            raise ValueError(
                f"Invalid unlock_recommendation {self.unlock_recommendation!r}; "
                f"must be one of {VALID_UNLOCK_RECOMMENDATIONS}"
            )
        if self.release_hold != "HOLD":
            raise ValueError(
                f"release_hold must be 'HOLD', got {self.release_hold!r}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "file_path": self.file_path,
            "risk_class": self.risk_class,
            "category": self.category,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "required_evidence": self.required_evidence,
            "promotion_readiness_default": self.promotion_readiness_default,
            "unlock_recommendation": self.unlock_recommendation,
            "release_hold": self.release_hold,
        }
