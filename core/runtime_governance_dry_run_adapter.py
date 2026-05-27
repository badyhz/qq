"""Runtime governance dry-run adapter — evaluates contract using failure stack.

Pure. No I/O. No network. No random. No timestamps. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_contract import (
    RuntimeGovernanceContractResult,
    RuntimeGovernanceInput,
    validate_runtime_governance_input,
    runtime_governance_input_to_dict,
)
from core.governance_failure_report import (
    GovernanceFailureReport,
    build_governance_failure_report,
    report_to_dict,
    report_to_markdown,
)
from core.governance_failure_regression_packet import (
    GovernanceFailureRegressionPacket,
    build_governance_failure_regression_packet,
    packet_to_dict,
    packet_to_markdown,
)
from core.governance_failure_verdict_matrix import resolve_governance_final_verdict


# ── result type ───────────────────────────────────────────────────────


@dataclass
class RuntimeGovernanceDryRunResult:
    """Result of evaluating governance contract in dry-run mode."""

    input: RuntimeGovernanceInput
    contract_result: RuntimeGovernanceContractResult
    report: GovernanceFailureReport
    packet: GovernanceFailureRegressionPacket
    final_verdict: str
    mode: str
    notes: List[str]


# ── core evaluation ───────────────────────────────────────────────────


def evaluate_runtime_governance_dry_run(
    inp: RuntimeGovernanceInput,
    *,
    expected_markdown: str | None = None,
    notes: List[str] | None = None,
) -> RuntimeGovernanceDryRunResult:
    """Evaluate governance contract in dry-run mode. Pure. No I/O."""
    extra_notes: List[str] = list(notes) if notes else []

    # step 1: validate input
    contract_result = validate_runtime_governance_input(inp)

    # step 2: build report from failures (empty list if contract ok)
    report = build_governance_failure_report(
        contract_result.failures,
        title="Runtime Governance Dry-Run Report",
        notes=contract_result.notes,
    )

    # step 3: build regression packet with optional snapshot
    packet = build_governance_failure_regression_packet(
        contract_result.failures,
        title="Runtime Governance Dry-Run Regression",
        expected_markdown=expected_markdown,
        notes=extra_notes,
    )

    # step 4: compute final verdict via verdict matrix
    snapshot_ok = packet.snapshot_diff.ok
    final_verdict = resolve_governance_final_verdict(report.verdict, snapshot_ok)

    return RuntimeGovernanceDryRunResult(
        input=inp,
        contract_result=contract_result,
        report=report,
        packet=packet,
        final_verdict=final_verdict,
        mode="dry_run",
        notes=extra_notes,
    )


# ── serialization ─────────────────────────────────────────────────────


def dry_run_result_to_dict(result: RuntimeGovernanceDryRunResult) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "input": runtime_governance_input_to_dict(result.input),
        "contract_result": {
            "ok": result.contract_result.ok,
            "failure_count": len(result.contract_result.failures),
            "notes": list(result.contract_result.notes),
        },
        "report": report_to_dict(result.report),
        "packet": packet_to_dict(result.packet),
        "final_verdict": result.final_verdict,
        "mode": result.mode,
        "notes": list(result.notes),
    }


def dry_run_result_to_markdown(result: RuntimeGovernanceDryRunResult) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines: List[str] = []

    lines.append("# Runtime Governance Dry-Run Result")
    lines.append("")

    lines.append(f"**Final Verdict:** {result.final_verdict}")
    lines.append(f"**Mode:** {result.mode}")
    lines.append(f"**Contract OK:** {result.contract_result.ok}")
    lines.append("")

    # input summary
    lines.append("## Input")
    lines.append("")
    lines.append(f"- **Run ID:** {result.input.run_id}")
    lines.append(f"- **Adapter ID:** {result.input.adapter_id}")
    lines.append(f"- **Mode:** {result.input.mode}")
    lines.append(f"- **Action:** {result.input.requested_action}")
    lines.append(f"- **Symbol:** {result.input.symbol}")
    lines.append(f"- **Environment:** {result.input.environment}")
    lines.append(f"- **Allow Submit:** {result.input.allow_submit}")
    lines.append(f"- **Allow Network:** {result.input.allow_network}")
    lines.append("")

    # report verdict
    lines.append("## Report")
    lines.append("")
    lines.append(f"**Verdict:** {result.report.verdict}")
    lines.append(f"**Total Failures:** {result.report.total_failures}")
    lines.append(f"**Critical:** {result.report.critical_count}")
    lines.append("")

    # snapshot
    lines.append("## Snapshot")
    lines.append("")
    lines.append(f"- **OK:** {result.packet.snapshot_diff.ok}")
    lines.append("")

    # notes
    all_notes = result.contract_result.notes + result.notes
    if all_notes:
        lines.append("## Notes")
        lines.append("")
        for note in all_notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
