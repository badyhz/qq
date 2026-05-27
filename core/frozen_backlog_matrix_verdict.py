"""T1377 - Frozen Backlog Matrix Verdict."""
from __future__ import annotations

from dataclasses import dataclass

VALID_VERDICTS: tuple[str, ...] = ("HOLD", "PASS", "BLOCKED", "PARTIAL")


@dataclass(frozen=True)
class FrozenBacklogMatrixVerdict:
    """Immutable matrix verdict.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    verdict: str
    notes: str
    blocked_items: tuple[str, ...]
    promotable_items: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "notes": self.notes,
            "blocked_items": self.blocked_items,
            "promotable_items": self.promotable_items,
        }


def build_verdict(
    verdict: str,
    notes: str = "",
    blocked_items: tuple[str, ...] = (),
    promotable_items: tuple[str, ...] = (),
) -> FrozenBacklogMatrixVerdict:
    """Factory with validation for FrozenBacklogMatrixVerdict."""
    if verdict not in VALID_VERDICTS:
        raise ValueError(
            f"Invalid verdict {verdict!r}; must be one of {VALID_VERDICTS}"
        )
    return FrozenBacklogMatrixVerdict(
        verdict=verdict,
        notes=notes,
        blocked_items=blocked_items,
        promotable_items=promotable_items,
    )
