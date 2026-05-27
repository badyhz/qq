"""Runtime governance dry-run matrix report — run all sample kinds through preflight.

Pure. No I/O. No network. No random. No timestamps. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.runtime_governance_sample_factory import (
    build_runtime_governance_sample_preflight_packet,
)
from core.runtime_governance_preflight_packet import (
    RuntimeGovernancePreflightPacket,
)
from core.governance_failure_taxonomy import FailureSeverity


# ── row type ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RuntimeGovernanceDryRunMatrixRow:
    """Single row in the dry-run matrix report."""

    kind: str
    final_verdict: str
    ready_for_runtime: bool
    blocker_count: int
    ok: bool


# ── kinds ──────────────────────────────────────────────────────────────

_MATRIX_KINDS: List[str] = ["pass", "fail", "blocked", "warn_like", "invalid_contract"]


# ── builders ───────────────────────────────────────────────────────────


def _count_blockers(packet: RuntimeGovernancePreflightPacket) -> int:
    """Count blockers: critical non-retryable failures in the contract result."""
    return sum(
        1
        for f in packet.dry_run_result.contract_result.failures
        if f.severity == FailureSeverity.CRITICAL and not f.retryable
    )


def _is_ready(packet: RuntimeGovernancePreflightPacket) -> bool:
    """Ready for runtime iff final_verdict is PASS and zero blockers."""
    return packet.final_verdict == "PASS" and packet.proceed


def build_runtime_governance_dry_run_matrix_report() -> List[RuntimeGovernanceDryRunMatrixRow]:
    """Build matrix report by running every sample kind through preflight.

    Pure. Deterministic. No I/O.
    """
    rows: List[RuntimeGovernanceDryRunMatrixRow] = []
    for kind in _MATRIX_KINDS:
        packet = build_runtime_governance_sample_preflight_packet(kind)
        blockers = _count_blockers(packet)
        ready = _is_ready(packet)
        rows.append(
            RuntimeGovernanceDryRunMatrixRow(
                kind=kind,
                final_verdict=packet.final_verdict,
                ready_for_runtime=ready,
                blocker_count=blockers,
                ok=packet.dry_run_result.contract_result.ok,
            )
        )
    return rows


# ── serialization ──────────────────────────────────────────────────────


def dry_run_matrix_to_dict(matrix: List[RuntimeGovernanceDryRunMatrixRow]) -> List[Dict[str, Any]]:
    """Serialize matrix to list of dicts. Deterministic."""
    return [
        {
            "kind": row.kind,
            "final_verdict": row.final_verdict,
            "ready_for_runtime": row.ready_for_runtime,
            "blocker_count": row.blocker_count,
            "ok": row.ok,
        }
        for row in matrix
    ]


def dry_run_matrix_to_markdown(matrix: List[RuntimeGovernanceDryRunMatrixRow]) -> str:
    """Render matrix as deterministic markdown table. No timestamps."""
    lines: List[str] = []

    lines.append("# Runtime Governance Dry-Run Matrix Report")
    lines.append("")
    lines.append(
        "| Kind | Final Verdict | Ready | Blockers | OK |"
    )
    lines.append(
        "|------|---------------|-------|----------|----|"
    )
    for row in matrix:
        ready = "yes" if row.ready_for_runtime else "no"
        ok = "yes" if row.ok else "no"
        lines.append(
            f"| {row.kind} | {row.final_verdict} | {ready} | {row.blocker_count} | {ok} |"
        )
    lines.append("")

    return "\n".join(lines)
