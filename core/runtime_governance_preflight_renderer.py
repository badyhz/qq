"""Runtime governance preflight renderer — pure rendering for PreflightPacket.

Deterministic. No timestamps. No I/O. No network. No random.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.runtime_governance_preflight_packet import RuntimeGovernancePreflightPacket
from core.runtime_governance_audit_event import audit_event_to_markdown
from core.governance_failure_taxonomy import FailureSeverity


def render_preflight_summary(packet: RuntimeGovernancePreflightPacket) -> Dict[str, Any]:
    """Compact summary dict. Pure. Deterministic."""
    contract = packet.dry_run_result.contract_result
    failures = contract.failures

    blockers = _extract_blockers(failures)

    return {
        "final_verdict": packet.final_verdict,
        "proceed": packet.proceed,
        "ready": packet.proceed and len(blockers) == 0,
        "blocker_count": len(blockers),
        "failure_count": len(failures),
        "contract_ok": contract.ok,
        "notes_count": len(packet.notes),
    }


def render_preflight_markdown(packet: RuntimeGovernancePreflightPacket) -> str:
    """Full markdown with sections. Deterministic. No timestamps."""
    contract = packet.dry_run_result.contract_result
    failures = contract.failures

    blockers = _extract_blockers(failures)
    sorted_blockers = sorted(blockers, key=lambda f: f.category.value)
    sorted_failures = sorted(failures, key=lambda f: f.category.value)

    ready = packet.proceed and len(blockers) == 0

    lines: List[str] = []

    # section 1
    lines.append("# Runtime Governance Preflight")
    lines.append("")

    # section 2
    lines.append("## Final Verdict")
    lines.append("")
    lines.append(f"- **verdict:** `{packet.final_verdict}`")
    lines.append(f"- **proceed:** {packet.proceed}")
    lines.append("")

    # section 3
    lines.append("## Ready For Runtime")
    lines.append("")
    lines.append(f"- {ready}")
    lines.append("")

    # section 4
    lines.append("## Blockers")
    lines.append("")
    if sorted_blockers:
        for f in sorted_blockers:
            lines.append(f"- [{f.category.value}] {f.severity.value}: {f.message}")
    else:
        lines.append("- (none)")
    lines.append("")

    # section 5
    lines.append("## Failures")
    lines.append("")
    if sorted_failures:
        for f in sorted_failures:
            retryable_str = "retryable" if f.retryable else "non-retryable"
            lines.append(f"- [{f.category.value}] {f.severity.value}: {f.message} ({retryable_str})")
    else:
        lines.append("- (none)")
    lines.append("")

    # section 6
    lines.append("## Audit Event")
    lines.append("")
    lines.append(audit_event_to_markdown(packet.audit_event))

    # section 7
    lines.append("## Notes")
    lines.append("")
    if packet.notes:
        for note in packet.notes:
            lines.append(f"- {note}")
    else:
        lines.append("- (none)")
    lines.append("")

    return "\n".join(lines)


def render_preflight_compact_dict(packet: RuntimeGovernancePreflightPacket) -> Dict[str, Any]:
    """Minimal dict for logging. Pure. Deterministic."""
    return {
        "verdict": packet.final_verdict,
        "proceed": packet.proceed,
        "failures": len(packet.dry_run_result.contract_result.failures),
    }


def _extract_blockers(failures):
    """Extract blockers: CRITICAL severity or non-retryable failures."""
    return [
        f for f in failures
        if f.severity == FailureSeverity.CRITICAL or not f.retryable
    ]
