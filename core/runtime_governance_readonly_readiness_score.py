"""T836 — Read-only readiness score for runtime governance.

Pure, deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.runtime_governance_readonly_regression_packet import (
    RuntimeGovernanceReadOnlyRegressionPacket,
)


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyReadinessScore:
    """Immutable readiness score for read-only layer."""

    score: int
    max_score: int
    percent: float
    grade: str  # A / B / C / D / F
    blockers: List[str]
    warnings: List[str]
    notes: List[str]


# ── constants ──────────────────────────────────────────────────────────

_MAX_SCORE = 100
_SCENARIO_FAIL_PENALTY = 20
_SIDE_EFFECT_FAIL_PENALTY = 25
_MANIFEST_FAIL_PENALTY = 20

_GRADE_THRESHOLDS = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (0, "F"),
]


# ── internal ───────────────────────────────────────────────────────────


def _raw_score(
    scenario_fail_count: int,
    side_effect_verdict: str,
    manifest_verdict: str,
) -> int:
    """Compute raw score by subtracting penalties. Pure."""
    s = _MAX_SCORE
    s -= scenario_fail_count * _SCENARIO_FAIL_PENALTY
    if side_effect_verdict != "PASS":
        s -= _SIDE_EFFECT_FAIL_PENALTY
    if manifest_verdict != "PASS":
        s -= _MANIFEST_FAIL_PENALTY
    return max(0, min(_MAX_SCORE, s))


def _grade(score: int, blocked: bool) -> str:
    """Resolve letter grade. BLOCKED caps at F. Pure."""
    if blocked:
        return "F"
    for threshold, g in _GRADE_THRESHOLDS:
        if score >= threshold:
            return g
    return "F"


def _collect_blockers(packet: RuntimeGovernanceReadOnlyRegressionPacket) -> List[str]:
    """Collect blocker strings. Pure."""
    blockers: List[str] = []
    if packet.final_verdict != "PASS":
        blockers.append(f"final_verdict={packet.final_verdict}")
    return blockers


def _collect_warnings(packet: RuntimeGovernanceReadOnlyRegressionPacket) -> List[str]:
    """Collect warning strings. Pure."""
    warnings: List[str] = []
    if packet.scenario_fail_count > 0:
        warnings.append(f"scenario_fail_count={packet.scenario_fail_count}")
    if packet.side_effect_verdict != "PASS":
        warnings.append(f"side_effect_verdict={packet.side_effect_verdict}")
    if packet.manifest_verdict != "PASS":
        warnings.append(f"manifest_verdict={packet.manifest_verdict}")
    return warnings


def _collect_notes(packet: RuntimeGovernanceReadOnlyRegressionPacket) -> List[str]:
    """Collect metadata notes. Pure."""
    notes: List[str] = list(packet.notes)
    notes.append(f"scenario_count={packet.scenario_count}")
    notes.append(f"scenario_pass_count={packet.scenario_pass_count}")
    return notes


# ── public API ─────────────────────────────────────────────────────────


def compute_readonly_readiness_score(
    packet: RuntimeGovernanceReadOnlyRegressionPacket,
) -> RuntimeGovernanceReadOnlyReadinessScore:
    """Compute readiness score from a read-only regression packet.

    Pure. Deterministic. No I/O.

    Scoring:
      - Start at 100
      - Each scenario fail: -20
      - Side-effect verdict != PASS: -25
      - Manifest verdict != PASS: -20
      - Final verdict != PASS: grade capped at F
      - Grade: A>=90, B>=75, C>=60, D>=40, F<40
    """
    score = _raw_score(
        scenario_fail_count=packet.scenario_fail_count,
        side_effect_verdict=packet.side_effect_verdict,
        manifest_verdict=packet.manifest_verdict,
    )

    blockers = _collect_blockers(packet)
    warnings = _collect_warnings(packet)
    notes = _collect_notes(packet)

    percent = round(score / _MAX_SCORE * 100, 1)

    has_blocker = len(blockers) > 0
    grade = _grade(score, has_blocker)

    return RuntimeGovernanceReadOnlyReadinessScore(
        score=score,
        max_score=_MAX_SCORE,
        percent=percent,
        grade=grade,
        blockers=blockers,
        warnings=warnings,
        notes=notes,
    )


def readonly_readiness_score_to_dict(
    score: RuntimeGovernanceReadOnlyReadinessScore,
) -> Dict[str, Any]:
    """Serialize score to plain dict. Deterministic."""
    return {
        "score": score.score,
        "max_score": score.max_score,
        "percent": score.percent,
        "grade": score.grade,
        "blockers": list(score.blockers),
        "warnings": list(score.warnings),
        "notes": list(score.notes),
    }


def readonly_readiness_score_to_markdown(
    score: RuntimeGovernanceReadOnlyReadinessScore,
) -> str:
    """Render score as deterministic markdown. No timestamps."""
    lines: List[str] = []

    lines.append("# Runtime Governance Read-Only Readiness Score")
    lines.append("")
    lines.append(f"**Score:** {score.score}/{score.max_score}")
    lines.append(f"**Percent:** {score.percent}%")
    lines.append(f"**Grade:** {score.grade}")
    lines.append("")

    if score.blockers:
        lines.append("## Blockers")
        lines.append("")
        for b in score.blockers:
            lines.append(f"- {b}")
        lines.append("")

    if score.warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in score.warnings:
            lines.append(f"- {w}")
        lines.append("")

    if score.notes:
        lines.append("## Notes")
        lines.append("")
        for n in score.notes:
            lines.append(f"- {n}")
        lines.append("")

    return "\n".join(lines)
