from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitReleaseGateVerdict:
    verdict: str
    invariant_violations: tuple[str, ...]
    denied_op_attempts: tuple[str, ...]
    notes: str


def build_verdict(
    verdict: str,
    invariant_violations: tuple[str, ...] = (),
    denied_op_attempts: tuple[str, ...] = (),
    notes: str = "",
) -> NoSubmitReleaseGateVerdict:
    return NoSubmitReleaseGateVerdict(
        verdict=verdict,
        invariant_violations=invariant_violations,
        denied_op_attempts=denied_op_attempts,
        notes=notes,
    )


def verdict_to_dict(v: NoSubmitReleaseGateVerdict) -> dict[str, object]:
    return {
        "verdict": v.verdict,
        "invariant_violations": list(v.invariant_violations),
        "denied_op_attempts": list(v.denied_op_attempts),
        "notes": v.notes,
    }
