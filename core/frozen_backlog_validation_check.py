"""T1603 - Frozen Backlog Validation Check.

Frozen dataclass for a single validation check result.
Pure deterministic. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogValidationCheck:
    """Immutable single validation check.

    Pure frozen. No I/O. No timestamps. No network.
    """

    check_id: str
    check_name: str
    expected_value: object
    actual_value: object
    passed: bool
    description: str
