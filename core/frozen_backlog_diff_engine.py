"""T1613 - Frozen Backlog Diff Engine.

Pure functions for computing diffs between two frozen backlog report dicts.
No I/O. No timestamps. No network.
"""
from __future__ import annotations

from core.frozen_backlog_diff import FrozenBacklogDiff
from core.frozen_diff_change import FrozenDiffChange


def _diff_file_fields(
    before_records: dict[str, dict],
    after_records: dict[str, dict],
    field_name: str,
) -> tuple[FrozenDiffChange, ...]:
    """Compare a single field across matched records. Pure function."""
    changes: list[FrozenDiffChange] = []
    common_files = set(before_records) & set(after_records)
    for fp in sorted(common_files):
        old_val = before_records[fp].get(field_name)
        new_val = after_records[fp].get(field_name)
        if old_val != new_val:
            changes.append(FrozenDiffChange(
                file_path=fp,
                field_name=field_name,
                old_value=old_val,
                new_value=new_val,
            ))
    return tuple(changes)


def _records_by_path(data: dict) -> dict[str, dict]:
    """Index records list by file_path. Pure function."""
    result: dict[str, dict] = {}
    for rec in data.get("records", []):
        fp = rec.get("file_path", "")
        result[fp] = rec
    return result


def diff_reports(
    before: dict,
    after: dict,
    diff_id: str = "diff",
    before_snapshot_id: str = "before",
    after_snapshot_id: str = "after",
) -> FrozenBacklogDiff:
    """Compare two report dicts and return a FrozenBacklogDiff. Pure function."""
    before_idx = _records_by_path(before)
    after_idx = _records_by_path(after)

    before_files = set(before_idx)
    after_files = set(after_idx)

    added = tuple(sorted(after_files - before_files))
    removed = tuple(sorted(before_files - after_files))

    return FrozenBacklogDiff(
        diff_id=diff_id,
        before_snapshot_id=before_snapshot_id,
        after_snapshot_id=after_snapshot_id,
        added_files=added,
        removed_files=removed,
        risk_class_changes=_diff_file_fields(before_idx, after_idx, "risk_class"),
        category_changes=_diff_file_fields(before_idx, after_idx, "category"),
        recommendation_changes=_diff_file_fields(
            before_idx, after_idx, "unlock_recommendation"
        ),
        safety_flag_changes=(),
        hold_changes=_diff_file_fields(before_idx, after_idx, "release_hold"),
    )


def has_changes(diff: FrozenBacklogDiff) -> bool:
    """Return True if any changes detected in the diff. Pure function."""
    return bool(
        diff.added_files
        or diff.removed_files
        or diff.risk_class_changes
        or diff.category_changes
        or diff.recommendation_changes
        or diff.safety_flag_changes
        or diff.hold_changes
    )
