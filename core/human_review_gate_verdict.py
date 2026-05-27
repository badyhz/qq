from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReviewGateVerdict:
    gate_id: str
    verdict: str
    issues: tuple[str, ...]
    notes: tuple[str, ...]


VALID_VERDICTS: frozenset[str] = frozenset({
    "PASS",
    "FAIL",
    "BLOCKED",
    "HOLD",
})


def build_verdict(
    gate_id: str,
    verdict: str,
    issues: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
) -> HumanReviewGateVerdict:
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"Invalid verdict: {verdict}. Must be one of {VALID_VERDICTS}")
    return HumanReviewGateVerdict(
        gate_id=gate_id,
        verdict=verdict,
        issues=tuple(issues),
        notes=tuple(notes),
    )


def verdict_to_dict(v: HumanReviewGateVerdict) -> dict[str, object]:
    return {
        "gate_id": v.gate_id,
        "verdict": v.verdict,
        "issues": list(v.issues),
        "notes": list(v.notes),
    }
