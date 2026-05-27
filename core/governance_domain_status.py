"""Governance Domain Status — T1365 frozen dataclass.

Status tracking for a governance domain.
Pure, frozen. No I/O. No network. No timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass

ALL_STATUSES = ("COMPLETE", "IN_PROGRESS", "BLOCKED", "HOLD")


@dataclass(frozen=True)
class GovernanceDomainStatus:
    """Status of a single governance domain."""
    domain_id: str
    status: str
    completion_pct: float
    blockers: tuple  # tuple of blocker description strings

    def __post_init__(self) -> None:
        if self.status not in ALL_STATUSES:
            raise ValueError(
                f"Invalid status {self.status!r}, expected one of {ALL_STATUSES}"
            )
