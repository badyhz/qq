"""T1615 - FrozenBacklogVerdict frozen dataclass.

Pure frozen dataclass for review verdict outcome.
No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogVerdict:
    """Immutable verdict from a frozen backlog review.

    Pure frozen. No I/O. No timestamps. No network.
    """

    verdict: str  # PASS / PARTIAL / FAIL
    notes: str
    changed_fields: tuple[str, ...]
    risk_level: str  # SAFE / CAUTION / CRITICAL


def build_verdict(
    verdict: str,
    notes: str,
    changed_fields: tuple[str, ...],
    risk_level: str,
) -> FrozenBacklogVerdict:
    """Build a FrozenBacklogVerdict. Pure function."""
    return FrozenBacklogVerdict(
        verdict=verdict,
        notes=notes,
        changed_fields=changed_fields,
        risk_level=risk_level,
    )
