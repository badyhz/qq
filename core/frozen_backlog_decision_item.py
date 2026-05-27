"""T1372 - Frozen Backlog Decision Item."""
from __future__ import annotations

from dataclasses import dataclass

VALID_RISK_CLASSES: tuple[str, ...] = ("HIGH", "MEDIUM")


@dataclass(frozen=True)
class FrozenBacklogDecisionItem:
    """Immutable backlog decision item.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    item_id: str
    file_path: str
    risk_class: str
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    current_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "file_path": self.file_path,
            "risk_class": self.risk_class,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "required_evidence": self.required_evidence,
            "current_state": self.current_state,
        }


def build_decision_item(
    item_id: str,
    file_path: str,
    risk_class: str,
    allowed_actions: tuple[str, ...] = (),
    forbidden_actions: tuple[str, ...] = (),
    required_evidence: tuple[str, ...] = (),
    current_state: str = "pending",
) -> FrozenBacklogDecisionItem:
    """Factory with validation for FrozenBacklogDecisionItem."""
    if risk_class not in VALID_RISK_CLASSES:
        raise ValueError(
            f"Invalid risk_class {risk_class!r}; must be one of {VALID_RISK_CLASSES}"
        )
    return FrozenBacklogDecisionItem(
        item_id=item_id,
        file_path=file_path,
        risk_class=risk_class,
        allowed_actions=allowed_actions,
        forbidden_actions=forbidden_actions,
        required_evidence=required_evidence,
        current_state=current_state,
    )
