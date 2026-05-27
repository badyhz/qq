"""T1611 - FrozenBacklogDiff frozen dataclass.

Pure frozen dataclass for the diff between two frozen backlog reports.
No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.frozen_diff_change import FrozenDiffChange


@dataclass(frozen=True)
class FrozenBacklogDiff:
    """Immutable diff between two frozen backlog report snapshots.

    Pure frozen. No I/O. No timestamps. No network.
    """

    diff_id: str
    before_snapshot_id: str
    after_snapshot_id: str
    added_files: tuple[str, ...]
    removed_files: tuple[str, ...]
    risk_class_changes: tuple[FrozenDiffChange, ...]
    category_changes: tuple[FrozenDiffChange, ...]
    recommendation_changes: tuple[FrozenDiffChange, ...]
    safety_flag_changes: tuple[FrozenDiffChange, ...]
    hold_changes: tuple[FrozenDiffChange, ...]
