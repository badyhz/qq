"""T855: Runtime governance read-only release hold packet.

Explicitly holds any real runtime release until manual approval.
Pure, deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyReleaseHoldPacket:
    """Frozen packet that holds runtime release until manual approval."""

    hold_active: bool = True
    hold_reasons: List[str] = field(default_factory=lambda: [
        "no manual approval",
        "read-only design only",
        "no live authorization",
        "no implementation authorized",
    ])
    allowed_actions: List[str] = field(default_factory=lambda: [
        "review design",
        "review tests",
        "review evidence",
        "review checklist",
    ])
    forbidden_actions: List[str] = field(default_factory=lambda: [
        "live trading",
        "order placement",
        "secret access",
        "network call",
        "planner integration",
        "file write",
    ])
    release_conditions: List[str] = field(default_factory=lambda: [
        "manual approval signed",
        "readiness score >= B",
        "blocker summary PROCEED",
        "evidence packet PASS",
        "transition checklist complete",
    ])
    final_verdict: str = "HOLD"


def build_readonly_release_hold_packet() -> RuntimeGovernanceReadOnlyReleaseHoldPacket:
    """Build a default read-only release hold packet."""
    return RuntimeGovernanceReadOnlyReleaseHoldPacket()


def readonly_release_hold_packet_to_dict(
    packet: RuntimeGovernanceReadOnlyReleaseHoldPacket,
) -> Dict:
    """Convert hold packet to dict."""
    return {
        "hold_active": packet.hold_active,
        "hold_reasons": list(packet.hold_reasons),
        "allowed_actions": list(packet.allowed_actions),
        "forbidden_actions": list(packet.forbidden_actions),
        "release_conditions": list(packet.release_conditions),
        "final_verdict": packet.final_verdict,
    }


def readonly_release_hold_packet_to_markdown(
    packet: RuntimeGovernanceReadOnlyReleaseHoldPacket,
) -> str:
    """Convert hold packet to markdown."""
    lines = [
        "# Runtime Governance Read-Only Release Hold Packet",
        "",
        f"**Hold Active:** {packet.hold_active}",
        f"**Final Verdict:** {packet.final_verdict}",
        "",
        "## Hold Reasons",
        "",
    ]
    for r in packet.hold_reasons:
        lines.append(f"- {r}")
    lines += ["", "## Allowed Actions", ""]
    for a in packet.allowed_actions:
        lines.append(f"- {a}")
    lines += ["", "## Forbidden Actions", ""]
    for a in packet.forbidden_actions:
        lines.append(f"- {a}")
    lines += ["", "## Release Conditions", ""]
    for c in packet.release_conditions:
        lines.append(f"- {c}")
    return "\n".join(lines) + "\n"
