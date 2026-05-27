"""Runtime governance manual scope packet — manual review scope summary.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceManualScopePacket:
    """Immutable manual scope packet for runtime governance."""

    title: str
    scope_items: List[str]
    verdict: str  # "PASS" / "WARN" / "FAIL"
    notes: List[str] = field(default_factory=list)


def build_runtime_governance_manual_scope_packet(
    *,
    title: str = "Runtime Governance Manual Scope Packet",
    scope_items: List[str] | None = None,
    verdict: str = "PASS",
    notes: List[str] | None = None,
) -> RuntimeGovernanceManualScopePacket:
    """Build manual scope packet. Pure. No I/O.

    Defaults produce a passing packet with standard scope items.
    """
    return RuntimeGovernanceManualScopePacket(
        title=title,
        scope_items=list(scope_items) if scope_items else [
            "phase_control_report_review",
            "risk_register_review",
            "artifact_index_review",
            "closeout_checklist_review",
        ],
        verdict=verdict,
        notes=list(notes) if notes else [],
    )


def summarize_manual_scope_packet(packet: RuntimeGovernanceManualScopePacket) -> Dict[str, Any]:
    """Summarize manual scope packet. Deterministic."""
    return {
        "title": packet.title,
        "item_count": len(packet.scope_items),
        "verdict": packet.verdict,
    }


def manual_scope_packet_to_dict(packet: RuntimeGovernanceManualScopePacket) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "title": packet.title,
        "scope_items": list(packet.scope_items),
        "verdict": packet.verdict,
        "notes": list(packet.notes),
    }


def manual_scope_packet_to_markdown(packet: RuntimeGovernanceManualScopePacket) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines: List[str] = [f"# {packet.title}", ""]
    lines.append(f"**Verdict:** {packet.verdict}")
    lines.append("")
    lines.append("## Scope Items")
    lines.append("")
    for item in packet.scope_items:
        lines.append(f"- {item}")
    lines.append("")
    if packet.notes:
        lines.append("## Notes")
        lines.append("")
        for note in packet.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
