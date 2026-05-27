from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumRiskReviewVerdict:
    """T1219 - frozen dataclass for review verdict."""

    verdict: str
    issues: tuple[str, ...]
    notes: tuple[str, ...]


def build_verdict(
    verdict: str,
    issues: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
) -> MediumRiskReviewVerdict:
    """Build a verdict. verdict must be one of PASS/FAIL/BLOCKED/HOLD."""
    valid = ("PASS", "FAIL", "BLOCKED", "HOLD")
    if verdict not in valid:
        raise ValueError(f"Invalid verdict: {verdict!r}. Must be one of {valid}")
    return MediumRiskReviewVerdict(
        verdict=verdict,
        issues=tuple(issues),
        notes=tuple(notes),
    )


def verdict_to_dict(v: MediumRiskReviewVerdict) -> dict[str, object]:
    """Convert verdict to a plain dict (no I/O)."""
    return {
        "verdict": v.verdict,
        "issues": list(v.issues),
        "notes": list(v.notes),
    }
