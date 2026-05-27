"""Runtime governance readiness score — pure scoring model.

Deterministic. No I/O. No network. No random. No timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_regression_packet import (
    RuntimeGovernanceRegressionPacket,
)


@dataclass(frozen=True)
class RuntimeGovernanceReadinessScore:
    """Immutable readiness score with grade, blockers, warnings."""

    score: int
    max_score: int
    percent: float
    grade: str  # A / B / C / D / F
    blockers: List[str]
    warnings: List[str]
    notes: List[str]


# ── constants ──────────────────────────────────────────────────────────

_MAX_SCORE = 100
_SCENARIO_FAIL_PENALTY = 10
_INVARIANT_ERROR_PENALTY = 5
_MANIFEST_WARN_PENALTY = 5
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
    invariant_error_count: int,
    manifest_verdict: str,
) -> int:
    """Compute raw score by subtracting penalties. Pure."""
    s = _MAX_SCORE
    s -= scenario_fail_count * _SCENARIO_FAIL_PENALTY
    s -= invariant_error_count * _INVARIANT_ERROR_PENALTY
    if manifest_verdict == "WARN":
        s -= _MANIFEST_WARN_PENALTY
    elif manifest_verdict == "FAIL":
        s -= _MANIFEST_FAIL_PENALTY
    return max(0, min(_MAX_SCORE, s))


def _grade(score: int, blocked: bool) -> str:
    """Resolve letter grade. BLOCKED blocker caps at F. Pure."""
    if blocked:
        return "F"
    for threshold, g in _GRADE_THRESHOLDS:
        if score >= threshold:
            return g
    return "F"


def _collect_blockers(packet: RuntimeGovernanceRegressionPacket) -> List[str]:
    """Collect blocker strings. Pure."""
    blockers: List[str] = []
    if packet.final_verdict == "BLOCKED":
        blockers.append("final_verdict=BLOCKED")
    if packet.final_verdict == "FAIL":
        blockers.append("final_verdict=FAIL")
    manifest_v = packet.manifest_summary.get("verdict", "UNKNOWN")
    if manifest_v == "FAIL":
        blockers.append("manifest_verdict=FAIL")
    if manifest_v == "BLOCKED":
        blockers.append("manifest_verdict=BLOCKED")
    return blockers


def _collect_warnings(packet: RuntimeGovernanceRegressionPacket) -> List[str]:
    """Collect warning strings. Pure."""
    warnings: List[str] = []
    manifest_v = packet.manifest_summary.get("verdict", "UNKNOWN")
    if manifest_v == "WARN":
        warnings.append("manifest_verdict=WARN")
    if packet.scenario_fail_count > 0:
        warnings.append(f"scenario_fail_count={packet.scenario_fail_count}")
    inv_errors = packet.invariant_summary.get("errors", 0)
    if inv_errors > 0:
        warnings.append(f"invariant_error_count={inv_errors}")
    return warnings


def _collect_notes(packet: RuntimeGovernanceRegressionPacket) -> List[str]:
    """Collect metadata notes. Pure."""
    notes: List[str] = list(packet.notes)
    notes.append(f"scenario_count={packet.scenario_count}")
    notes.append(f"scenario_pass_count={packet.scenario_pass_count}")
    notes.append(f"invariant_errors={packet.invariant_summary.get('errors', 0)}")
    notes.append(f"manifest_verdict={packet.manifest_summary.get('verdict', 'UNKNOWN')}")
    return notes


# ── public API ─────────────────────────────────────────────────────────


def compute_runtime_governance_readiness_score(
    packet: RuntimeGovernanceRegressionPacket,
) -> RuntimeGovernanceReadinessScore:
    """Compute readiness score from a regression packet.

    Pure. Deterministic. No I/O.

    Scoring:
      - Start at 100
      - Each scenario fail: -10
      - Each invariant error: -5
      - Manifest WARN: -5
      - Manifest FAIL: -20
      - Grade: A>=90, B>=75, C>=60, D>=40, F<40
      - Any BLOCKED blocker caps grade at F
    """
    inv_errors = packet.invariant_summary.get("errors", 0)
    manifest_v = packet.manifest_summary.get("verdict", "UNKNOWN")

    score = _raw_score(
        scenario_fail_count=packet.scenario_fail_count,
        invariant_error_count=inv_errors,
        manifest_verdict=manifest_v,
    )

    blockers = _collect_blockers(packet)
    warnings = _collect_warnings(packet)
    notes = _collect_notes(packet)

    percent = round(score / _MAX_SCORE * 100, 1)

    has_blocked = any("BLOCKED" in b for b in blockers)
    grade = _grade(score, has_blocked)

    return RuntimeGovernanceReadinessScore(
        score=score,
        max_score=_MAX_SCORE,
        percent=percent,
        grade=grade,
        blockers=blockers,
        warnings=warnings,
        notes=notes,
    )


def readiness_score_to_dict(
    score: RuntimeGovernanceReadinessScore,
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


def readiness_score_to_markdown(
    score: RuntimeGovernanceReadinessScore,
) -> str:
    """Render score as deterministic markdown. No timestamps."""
    lines: List[str] = []

    lines.append("# Runtime Governance Readiness Score")
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
