"""T1524 - Frozen Backlog Report Summary."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogReportSummary:
    """Immutable report summary for the frozen backlog.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    summary_id: str
    total_files: int
    high_risk_count: int
    medium_risk_count: int
    release_hold: str
    no_live: bool
    no_submit: bool
    no_exchange: bool
    no_runtime_integration: bool
    no_planner_integration: bool

    def __post_init__(self) -> None:
        if self.release_hold != "HOLD":
            raise ValueError(
                f"release_hold must be 'HOLD', got {self.release_hold!r}"
            )
        for field_name in (
            "no_live",
            "no_submit",
            "no_exchange",
            "no_runtime_integration",
            "no_planner_integration",
        ):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must be True")

    def to_dict(self) -> dict[str, object]:
        return {
            "summary_id": self.summary_id,
            "total_files": self.total_files,
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "release_hold": self.release_hold,
            "no_live": self.no_live,
            "no_submit": self.no_submit,
            "no_exchange": self.no_exchange,
            "no_runtime_integration": self.no_runtime_integration,
            "no_planner_integration": self.no_planner_integration,
        }
