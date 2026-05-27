"""T1119 - Freeze-Aware Queue Verdict."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreezeAwareQueueVerdict:
    """Immutable queue verdict.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    verdict: str
    admitted_count: int
    denied_count: int
    blocked_count: int
    notes: str


def build_verdict(
    verdict: str,
    admitted_count: int = 0,
    denied_count: int = 0,
    blocked_count: int = 0,
    notes: str = "",
) -> FreezeAwareQueueVerdict:
    """Factory for FreezeAwareQueueVerdict."""
    return FreezeAwareQueueVerdict(
        verdict=verdict,
        admitted_count=admitted_count,
        denied_count=denied_count,
        blocked_count=blocked_count,
        notes=notes,
    )


def verdict_to_dict(v: FreezeAwareQueueVerdict) -> dict:
    """Convert verdict to a plain dict."""
    return {
        "verdict": v.verdict,
        "admitted_count": v.admitted_count,
        "denied_count": v.denied_count,
        "blocked_count": v.blocked_count,
        "notes": v.notes,
    }
