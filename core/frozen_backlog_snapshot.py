"""T1606: FrozenBacklogSnapshot frozen dataclass."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FrozenBacklogSnapshot:
    """Immutable snapshot of a frozen backlog report."""

    snapshot_id: str
    report_data: dict[str, Any]
    created_at_iso: str
    version: str
