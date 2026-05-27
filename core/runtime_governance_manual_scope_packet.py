"""Runtime governance manual scope packet — define human review scope.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceManualScopePacket:
    """Immutable manual scope packet."""
    allowed_next_steps: List[str]
    forbidden_next_steps: List[str]
    required_reviews: List[str]
    final_scope: str
    notes: List[str] = field(default_factory=list)


_DEFAULT_ALLOWED = sorted([
    "review preflight results",
    "review regression packet",
    "scope future tasks",
    "dry-run design review",
    "frozen boundary review",
])

_DEFAULT_FORBIDDEN = sorted([
    "live trading",
    "real submit",
    "planner autonomous integration",
    "secret access",
    "account state mutation",
])

_DEFAULT_REQUIRED_REVIEWS = sorted([
    "pre-flight packet review",
    "regression packet review",
    "no-submit evidence review",
    "phase control report review",
])

_DEFAULT_NOTES = [
    "No live trading authorization in this phase.",
    "All next steps require manual human approval.",
]


def build_runtime_governance_manual_scope_packet(
    *,
    allowed_next_steps: List[str] | None = None,
    forbidden_next_steps: List[str] | None = None,
    required_reviews: List[str] | None = None,
    final_scope: str = "manual review and read-only analysis only",
    notes: List[str] | None = None,
) -> RuntimeGovernanceManualScopePacket:
    """Build manual scope packet. Pure. No I/O."""
    return RuntimeGovernanceManualScopePacket(
        allowed_next_steps=list(allowed_next_steps) if allowed_next_steps is not None else list(_DEFAULT_ALLOWED),
        forbidden_next_steps=list(forbidden_next_steps) if forbidden_next_steps is not None else list(_DEFAULT_FORBIDDEN),
        required_reviews=list(required_reviews) if required_reviews is not None else list(_DEFAULT_REQUIRED_REVIEWS),
        final_scope=final_scope,
        notes=list(notes) if notes is not None else list(_DEFAULT_NOTES),
    )


def summarize_manual_scope_packet(packet: RuntimeGovernanceManualScopePacket) -> Dict[str, Any]:
    """Summarize manual scope packet. Deterministic."""
    return {
        "item_count": len(packet.allowed_next_steps) + len(packet.forbidden_next_steps) + len(packet.required_reviews),
        "verdict": "PASS",
    }


def manual_scope_packet_to_dict(packet: RuntimeGovernanceManualScopePacket) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "allowed_next_steps": list(packet.allowed_next_steps),
        "forbidden_next_steps": list(packet.forbidden_next_steps),
        "required_reviews": list(packet.required_reviews),
        "final_scope": packet.final_scope,
        "notes": list(packet.notes),
    }


def manual_scope_packet_to_markdown(packet: RuntimeGovernanceManualScopePacket) -> str:
    """Render as deterministic markdown."""
    lines = [
        "# Manual Scope Packet",
        "",
        f"**Final Scope:** {packet.final_scope}",
        "",
        "## Allowed Next Steps",
        "",
    ]
    for step in packet.allowed_next_steps:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Forbidden Next Steps")
    lines.append("")
    for step in packet.forbidden_next_steps:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Required Reviews")
    lines.append("")
    for review in packet.required_reviews:
        lines.append(f"- {review}")
    lines.append("")
    if packet.notes:
        lines.append("## Notes")
        lines.append("")
        for note in packet.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
