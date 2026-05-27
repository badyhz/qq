"""Governance failure verdict matrix — pure decision table.

Maps (report_verdict, snapshot_ok) -> final_verdict.
No file I/O. No network. No runtime dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class GovernanceVerdictCase:
    """Single row in the verdict matrix."""
    report_verdict: str
    snapshot_ok: bool
    expected_final_verdict: str
    reason: str


# ── core logic ────────────────────────────────────────────────────────


def resolve_governance_final_verdict(report_verdict: str, snapshot_ok: bool) -> str:
    """Pure function: compute final verdict from report verdict + snapshot status.

    Rules:
    - BLOCKED wins regardless of snapshot
    - If snapshot not ok: FAIL (unless BLOCKED)
    - If snapshot ok: pass through report_verdict (PASS/WARN/FAIL)
    - Unknown report verdict => FAIL
    """
    if report_verdict == "BLOCKED":
        return "BLOCKED"
    if not snapshot_ok:
        return "FAIL"
    if report_verdict in ("PASS", "WARN", "FAIL"):
        return report_verdict
    return "FAIL"


# ── matrix builder ────────────────────────────────────────────────────

_MATRIX_CASES: List[GovernanceVerdictCase] = [
    GovernanceVerdictCase("PASS",    True,  "PASS",    "report PASS + snapshot ok"),
    GovernanceVerdictCase("WARN",    True,  "WARN",    "report WARN + snapshot ok"),
    GovernanceVerdictCase("FAIL",    True,  "FAIL",    "report FAIL + snapshot ok"),
    GovernanceVerdictCase("BLOCKED", True,  "BLOCKED", "report BLOCKED + snapshot ok"),
    GovernanceVerdictCase("PASS",    False, "FAIL",    "report PASS + snapshot not ok"),
    GovernanceVerdictCase("WARN",    False, "FAIL",    "report WARN + snapshot not ok"),
    GovernanceVerdictCase("FAIL",    False, "FAIL",    "report FAIL + snapshot not ok"),
    GovernanceVerdictCase("BLOCKED", False, "BLOCKED", "report BLOCKED always BLOCKED"),
    GovernanceVerdictCase("UNKNOWN", False, "FAIL",    "unknown report verdict"),
]


def build_governance_verdict_matrix() -> List[GovernanceVerdictCase]:
    """Return the full verdict matrix. Deterministic, no side effects."""
    return list(_MATRIX_CASES)


# ── serialization ─────────────────────────────────────────────────────


def verdict_matrix_to_dict(matrix: List[GovernanceVerdictCase]) -> List[Dict[str, Any]]:
    """Serialize matrix to list of dicts. Deterministic."""
    return [
        {
            "report_verdict": c.report_verdict,
            "snapshot_ok": c.snapshot_ok,
            "expected_final_verdict": c.expected_final_verdict,
            "reason": c.reason,
        }
        for c in matrix
    ]


def verdict_matrix_to_markdown(matrix: List[GovernanceVerdictCase]) -> str:
    """Render matrix as deterministic markdown. Stable ordering, no timestamps."""
    lines: List[str] = []

    lines.append("# Governance Failure Verdict Matrix")
    lines.append("")
    lines.append("Deterministic mapping of (report_verdict, snapshot_ok) -> final_verdict.")
    lines.append("")
    lines.append("| Report Verdict | Snapshot OK | Final Verdict | Reason |")
    lines.append("|----------------|-------------|---------------|--------|")
    for c in matrix:
        snap = "yes" if c.snapshot_ok else "no"
        lines.append(
            f"| {c.report_verdict} | {snap} | {c.expected_final_verdict} | {c.reason} |"
        )
    lines.append("")

    return "\n".join(lines)
