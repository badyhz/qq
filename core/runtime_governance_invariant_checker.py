"""Pure invariant checker for runtime governance inputs.

Deterministic. No timestamps. No random. No I/O. No network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_contract import ALLOWED_MODES, RuntimeGovernanceInput


@dataclass(frozen=True)
class RuntimeGovernanceInvariantResult:
    """Single invariant check result."""

    ok: bool
    invariant_id: str
    message: str
    severity: str  # "info", "warning", "error"
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── invariant checks ──────────────────────────────────────────────────


def check_runtime_governance_invariants(
    inp: RuntimeGovernanceInput,
) -> List[RuntimeGovernanceInvariantResult]:
    """Check all invariants against a RuntimeGovernanceInput.

    Deterministic. No I/O. Returns all results (pass and fail).
    """
    results: List[RuntimeGovernanceInvariantResult] = []

    # 1. no_submit_outside_test_or_testnet
    _submit_ok = not inp.allow_submit or inp.environment in ("test", "testnet")
    results.append(
        RuntimeGovernanceInvariantResult(
            ok=_submit_ok,
            invariant_id="no_submit_outside_test_or_testnet",
            message=(
                "submit allowed only in test/testnet"
                if not _submit_ok
                else "submit policy ok"
            ),
            severity="error" if not _submit_ok else "info",
            metadata={
                "allow_submit": inp.allow_submit,
                "environment": inp.environment,
            },
        )
    )

    # 2. no_network_without_explicit_mode
    _net_ok = not inp.allow_network or inp.mode != ""
    results.append(
        RuntimeGovernanceInvariantResult(
            ok=_net_ok,
            invariant_id="no_network_without_explicit_mode",
            message=(
                "network requires explicit mode"
                if not _net_ok
                else "network mode policy ok"
            ),
            severity="error" if not _net_ok else "info",
            metadata={"allow_network": inp.allow_network, "mode": inp.mode},
        )
    )

    # 3. mode_must_be_known
    _mode_ok = inp.mode in ALLOWED_MODES
    results.append(
        RuntimeGovernanceInvariantResult(
            ok=_mode_ok,
            invariant_id="mode_must_be_known",
            message=(
                f"unknown mode: {inp.mode}"
                if not _mode_ok
                else "mode recognized"
            ),
            severity="error" if not _mode_ok else "info",
            metadata={"mode": inp.mode, "allowed": sorted(ALLOWED_MODES)},
        )
    )

    # 4. adapter_id_required
    _adapter_ok = bool(inp.adapter_id)
    results.append(
        RuntimeGovernanceInvariantResult(
            ok=_adapter_ok,
            invariant_id="adapter_id_required",
            message="missing adapter_id" if not _adapter_ok else "adapter_id present",
            severity="error" if not _adapter_ok else "info",
            metadata={"adapter_id": inp.adapter_id},
        )
    )

    # 5. run_id_required
    _run_ok = bool(inp.run_id)
    results.append(
        RuntimeGovernanceInvariantResult(
            ok=_run_ok,
            invariant_id="run_id_required",
            message="missing run_id" if not _run_ok else "run_id present",
            severity="error" if not _run_ok else "info",
            metadata={"run_id": inp.run_id},
        )
    )

    # 6. file_io_default_false_for_shadow
    _fio_ok = not (inp.mode == "shadow" and inp.allow_file_io)
    results.append(
        RuntimeGovernanceInvariantResult(
            ok=_fio_ok,
            invariant_id="file_io_default_false_for_shadow",
            message=(
                "file_io should be false in shadow mode"
                if not _fio_ok
                else "shadow file_io policy ok"
            ),
            severity="warning" if not _fio_ok else "info",
            metadata={"mode": inp.mode, "allow_file_io": inp.allow_file_io},
        )
    )

    return results


# ── summary / serialization ───────────────────────────────────────────


def summarize_runtime_governance_invariants(
    results: List[RuntimeGovernanceInvariantResult],
) -> Dict[str, Any]:
    """Summarize invariant results into counts.

    Deterministic. No I/O.
    """
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


def invariants_to_dict(
    results: List[RuntimeGovernanceInvariantResult],
) -> List[Dict[str, Any]]:
    """Serialize invariant results to plain dicts.

    Deterministic. No I/O.
    """
    return [
        {
            "ok": r.ok,
            "invariant_id": r.invariant_id,
            "message": r.message,
            "severity": r.severity,
            "metadata": dict(r.metadata),
        }
        for r in results
    ]


def invariants_to_markdown(
    results: List[RuntimeGovernanceInvariantResult],
) -> str:
    """Render invariant results as markdown.

    Deterministic. No I/O. No timestamps.
    """
    lines: List[str] = ["# Runtime Governance Invariants", ""]
    lines.append("| # | invariant_id | ok | severity | message |")
    lines.append("|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        ok_sym = "PASS" if r.ok else "FAIL"
        lines.append(
            f"| {i} | {r.invariant_id} | {ok_sym} | {r.severity} | {r.message} |"
        )

    summary = summarize_runtime_governance_invariants(results)
    lines.append("")
    lines.append(f"**Total:** {summary['total']}  ")
    lines.append(f"**Passed:** {summary['passed']}  ")
    lines.append(f"**Failed:** {summary['failed']}  ")
    lines.append(f"**Errors:** {summary['errors']}  ")
    lines.append(f"**Warnings:** {summary['warnings']}  ")
    lines.append(f"**All ok:** {summary['all_ok']}  ")

    return "\n".join(lines) + "\n"
