"""T1862 - Frozen Backlog Manifest.

Frozen dataclass for the manifest of a board packet bundle.
Pure deterministic. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.frozen_backlog_artifact_entry import ArtifactEntry


@dataclass(frozen=True)
class FrozenBacklogManifest:
    """Immutable manifest for a frozen backlog review bundle.

    Pure frozen. No I/O. No timestamps. No network.
    Enforces safety invariants on construction.
    """

    manifest_id: str
    artifacts: tuple[ArtifactEntry, ...]
    generated_by: str
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
            "manifest_id": self.manifest_id,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "generated_by": self.generated_by,
            "release_hold": self.release_hold,
            "no_live": self.no_live,
            "no_submit": self.no_submit,
            "no_exchange": self.no_exchange,
            "no_runtime_integration": self.no_runtime_integration,
            "no_planner_integration": self.no_planner_integration,
        }
