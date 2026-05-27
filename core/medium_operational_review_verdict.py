"""T1319 — Medium operational review verdict model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalReviewVerdict:
    """Verdict produced after reviewing medium-risk operational scripts."""

    verdict: str
    notes: str
    violations: tuple[str, ...]

    def is_approved(self) -> bool:
        return self.verdict == "APPROVED"

    def is_denied(self) -> bool:
        return self.verdict == "DENIED"

    def is_hold(self) -> bool:
        return self.verdict == "HOLD"

    def violation_count(self) -> int:
        return len(self.violations)

    def violation_set(self) -> frozenset[str]:
        return frozenset(self.violations)

    def has_violations(self) -> bool:
        return len(self.violations) > 0


VALID_VERDICTS = frozenset({"APPROVED", "DENIED", "HOLD"})


def build_verdict(
    verdict: str,
    notes: str,
    violations: tuple[str, ...],
) -> MediumOperationalReviewVerdict:
    """Validate and construct a MediumOperationalReviewVerdict.

    Raises ValueError if verdict is not one of APPROVED / DENIED / HOLD.
    """
    if verdict not in VALID_VERDICTS:
        raise ValueError(
            f"Invalid verdict '{verdict}'; must be one of {sorted(VALID_VERDICTS)}"
        )
    if violations and verdict == "APPROVED":
        raise ValueError("Cannot approve with violations present")
    return MediumOperationalReviewVerdict(
        verdict=verdict,
        notes=notes,
        violations=violations,
    )
