from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VerdictValue(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    HOLD = "HOLD"


@dataclass(frozen=True)
class ReadinessScoringVerdict:
    """Frozen verdict. No I/O, no timestamps."""

    verdict: VerdictValue
    score_pct: float
    blockers: tuple  # tuple of ReadinessBlocker
    notes: str

    def build_verdict(self) -> VerdictValue:
        """Return current verdict value."""
        return self.verdict

    def verdict_to_dict(self) -> dict:
        """Export verdict as plain dict."""
        return {
            "verdict": self.verdict.value,
            "score_pct": self.score_pct,
            "blocker_count": len(self.blockers),
            "notes": self.notes,
        }
