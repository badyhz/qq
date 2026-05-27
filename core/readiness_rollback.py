from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessRollback:
    """Frozen rollback plan. No I/O, no timestamps."""

    change_id: str
    rollback_steps: tuple  # tuple of str
    verification_command: str
    reversible: bool
