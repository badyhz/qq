"""T1607: Pure functions for FrozenBacklogSnapshot management."""
from __future__ import annotations

import json
from typing import Any

from core.frozen_backlog_snapshot import FrozenBacklogSnapshot


def create_snapshot(
    report_data: dict[str, Any],
    version: str,
    created_at_iso: str,
    snapshot_id: str = "",
) -> FrozenBacklogSnapshot:
    """Create snapshot from report data."""
    return FrozenBacklogSnapshot(
        snapshot_id=snapshot_id,
        report_data=report_data,
        created_at_iso=created_at_iso,
        version=version,
    )


def snapshot_to_dict(snapshot: FrozenBacklogSnapshot) -> dict[str, Any]:
    """Convert snapshot to dict for JSON serialization."""
    return {
        "snapshot_id": snapshot.snapshot_id,
        "report_data": snapshot.report_data,
        "created_at_iso": snapshot.created_at_iso,
        "version": snapshot.version,
    }


def dict_to_snapshot(data: dict[str, Any]) -> FrozenBacklogSnapshot:
    """Convert dict back to snapshot."""
    return FrozenBacklogSnapshot(
        snapshot_id=data["snapshot_id"],
        report_data=data["report_data"],
        created_at_iso=data["created_at_iso"],
        version=data["version"],
    )


def write_snapshot(snapshot: FrozenBacklogSnapshot, output_path: str) -> None:
    """Write snapshot as JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_to_dict(snapshot), f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def read_snapshot(input_path: str) -> FrozenBacklogSnapshot:
    """Read snapshot from JSON file."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return dict_to_snapshot(data)
