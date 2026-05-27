"""T832 — Read-only invariant checker for permission envelopes.

Deterministic. No timestamps. No random. No I/O. No network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.runtime_governance_permission_envelope import (
    RuntimeGovernancePermissionEnvelope,
)


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyInvariant:
    """Single read-only invariant check result."""

    invariant_id: str
    ok: bool
    severity: str  # "info", "warning", "error"
    message: str


# ── invariant checks ──────────────────────────────────────────────────


def check_readonly_permission_invariants(
    envelope: RuntimeGovernancePermissionEnvelope,
) -> List[RuntimeGovernanceReadOnlyInvariant]:
    """Check invariants against a permission envelope. Pure.

    Invariants:
    1. no_write            — allow_write must be False
    2. no_network          — allow_network must be False
    3. no_order            — allow_order must be False
    4. no_account_mutation — allow_account_mutation must be False
    5. no_secret_access    — allow_secret_access must be False
    6. read_allowed        — allow_read must be True
    """
    results: List[RuntimeGovernanceReadOnlyInvariant] = []

    # 1. no_write
    _nw = not envelope.allow_write
    results.append(
        RuntimeGovernanceReadOnlyInvariant(
            invariant_id="no_write",
            ok=_nw,
            severity="error" if not _nw else "info",
            message="write permission must be disabled" if not _nw else "write blocked",
        )
    )

    # 2. no_network
    _nn = not envelope.allow_network
    results.append(
        RuntimeGovernanceReadOnlyInvariant(
            invariant_id="no_network",
            ok=_nn,
            severity="error" if not _nn else "info",
            message="network permission must be disabled" if not _nn else "network blocked",
        )
    )

    # 3. no_order
    _no = not envelope.allow_order
    results.append(
        RuntimeGovernanceReadOnlyInvariant(
            invariant_id="no_order",
            ok=_no,
            severity="error" if not _no else "info",
            message="order permission must be disabled" if not _no else "order blocked",
        )
    )

    # 4. no_account_mutation
    _am = not envelope.allow_account_mutation
    results.append(
        RuntimeGovernanceReadOnlyInvariant(
            invariant_id="no_account_mutation",
            ok=_am,
            severity="error" if not _am else "info",
            message="account mutation must be disabled" if not _am else "account mutation blocked",
        )
    )

    # 5. no_secret_access
    _sa = not envelope.allow_secret_access
    results.append(
        RuntimeGovernanceReadOnlyInvariant(
            invariant_id="no_secret_access",
            ok=_sa,
            severity="error" if not _sa else "info",
            message="secret access must be disabled" if not _sa else "secret access blocked",
        )
    )

    # 6. read_allowed
    _ra = envelope.allow_read
    results.append(
        RuntimeGovernanceReadOnlyInvariant(
            invariant_id="read_allowed",
            ok=_ra,
            severity="error" if not _ra else "info",
            message="read permission must be enabled" if not _ra else "read allowed",
        )
    )

    return results


# ── summary / serialization ───────────────────────────────────────────


def summarize_readonly_invariants(
    results: List[RuntimeGovernanceReadOnlyInvariant],
) -> Dict[str, Any]:
    """Summarize. Deterministic. No I/O."""
    total = len(results)
    passed = sum(1 for r in results if r.ok)
    failed = total - passed
    errors = sum(1 for r in results if not r.ok and r.severity == "error")
    warnings = sum(1 for r in results if not r.ok and r.severity == "warning")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "warnings": warnings,
        "all_ok": failed == 0,
    }


def readonly_invariants_to_dict(
    results: List[RuntimeGovernanceReadOnlyInvariant],
) -> List[Dict[str, Any]]:
    """Serialize. Deterministic. No I/O."""
    return [
        {
            "invariant_id": r.invariant_id,
            "ok": r.ok,
            "severity": r.severity,
            "message": r.message,
        }
        for r in results
    ]


def readonly_invariants_to_markdown(
    results: List[RuntimeGovernanceReadOnlyInvariant],
) -> str:
    """Deterministic markdown. No timestamps."""
    lines: List[str] = ["# Read-Only Invariants", ""]
    lines.append("| # | invariant_id | ok | severity | message |")
    lines.append("|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        ok_sym = "PASS" if r.ok else "FAIL"
        lines.append(
            f"| {i} | {r.invariant_id} | {ok_sym} | {r.severity} | {r.message} |"
        )

    summary = summarize_readonly_invariants(results)
    lines.append("")
    lines.append(f"**Total:** {summary['total']}  ")
    lines.append(f"**Passed:** {summary['passed']}  ")
    lines.append(f"**Failed:** {summary['failed']}  ")
    lines.append(f"**Errors:** {summary['errors']}  ")
    lines.append(f"**Warnings:** {summary['warnings']}  ")
    lines.append(f"**All ok:** {summary['all_ok']}  ")

    return "\n".join(lines) + "\n"
