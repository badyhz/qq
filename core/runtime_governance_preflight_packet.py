"""Runtime governance preflight packet — combines contract + dry-run + audit.

Pure. No I/O. No network. No random. No timestamps. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_contract import (
    RuntimeGovernanceInput,
    runtime_governance_input_to_dict,
)
from core.runtime_governance_dry_run_adapter import (
    RuntimeGovernanceDryRunResult,
    evaluate_runtime_governance_dry_run,
    dry_run_result_to_dict,
    dry_run_result_to_markdown,
)
from core.runtime_governance_audit_event import (
    RuntimeGovernanceAuditEvent,
    build_runtime_governance_audit_event,
    audit_event_to_dict,
    audit_event_to_markdown,
)


@dataclass(frozen=True)
class RuntimeGovernancePreflightPacket:
    """Immutable preflight packet for runtime governance decisions."""

    input: RuntimeGovernanceInput
    dry_run_result: RuntimeGovernanceDryRunResult
    audit_event: RuntimeGovernanceAuditEvent
    final_verdict: str
    proceed: bool
    notes: List[str] = field(default_factory=list)


# ── builder ───────────────────────────────────────────────────────────


def build_runtime_governance_preflight_packet(
    inp: RuntimeGovernanceInput,
    *,
    expected_markdown: str | None = None,
    notes: List[str] | None = None,
) -> RuntimeGovernancePreflightPacket:
    """Build preflight packet from input. Pure. No I/O.

    Steps:
    1. evaluate_runtime_governance_dry_run(inp, expected_markdown=expected_markdown)
    2. build audit event from dry_run_result
    3. final_verdict from dry_run_result.final_verdict
    4. proceed = (final_verdict == "PASS")
    """
    extra_notes: List[str] = list(notes) if notes else []

    # step 1: dry-run evaluation
    dry_run_result = evaluate_runtime_governance_dry_run(
        inp, expected_markdown=expected_markdown, notes=extra_notes,
    )

    # step 2: build audit event
    audit_event = build_runtime_governance_audit_event(
        run_id=inp.run_id,
        adapter_id=inp.adapter_id,
        action=inp.requested_action,
        verdict=dry_run_result.final_verdict,
        failures=dry_run_result.contract_result.failures,
    )

    # step 3-4: verdict and proceed
    final_verdict = dry_run_result.final_verdict
    proceed = final_verdict == "PASS"

    # collect all notes
    all_notes = list(extra_notes)

    return RuntimeGovernancePreflightPacket(
        input=inp,
        dry_run_result=dry_run_result,
        audit_event=audit_event,
        final_verdict=final_verdict,
        proceed=proceed,
        notes=all_notes,
    )


# ── serialization ─────────────────────────────────────────────────────


def preflight_packet_to_dict(packet: RuntimeGovernancePreflightPacket) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "input": runtime_governance_input_to_dict(packet.input),
        "dry_run_result": dry_run_result_to_dict(packet.dry_run_result),
        "audit_event": audit_event_to_dict(packet.audit_event),
        "final_verdict": packet.final_verdict,
        "proceed": packet.proceed,
        "notes": list(packet.notes),
    }


def preflight_packet_to_markdown(packet: RuntimeGovernancePreflightPacket) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines: List[str] = []

    lines.append("# Runtime Governance Preflight Packet")
    lines.append("")
    lines.append(f"**Final Verdict:** {packet.final_verdict}")
    lines.append(f"**Proceed:** {packet.proceed}")
    lines.append("")

    # input summary
    lines.append("## Input")
    lines.append("")
    lines.append(f"- **Run ID:** {packet.input.run_id}")
    lines.append(f"- **Adapter ID:** {packet.input.adapter_id}")
    lines.append(f"- **Mode:** {packet.input.mode}")
    lines.append(f"- **Action:** {packet.input.requested_action}")
    lines.append(f"- **Symbol:** {packet.input.symbol}")
    lines.append(f"- **Environment:** {packet.input.environment}")
    lines.append(f"- **Allow Submit:** {packet.input.allow_submit}")
    lines.append(f"- **Allow Network:** {packet.input.allow_network}")
    lines.append("")

    # dry-run result
    lines.append("## Dry-Run Result")
    lines.append("")
    lines.append(f"**Verdict:** {packet.dry_run_result.final_verdict}")
    lines.append(f"**Contract OK:** {packet.dry_run_result.contract_result.ok}")
    lines.append("")

    # audit event
    lines.append(audit_event_to_markdown(packet.audit_event))

    # notes
    all_notes = list(packet.notes)
    if all_notes:
        lines.append("## Notes")
        lines.append("")
        for note in all_notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
