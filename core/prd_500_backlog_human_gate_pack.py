"""T914 — 500 backlog human gate pack.

Pure deterministic. No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem

# --- Dataclass ---


@dataclass(frozen=True)
class Prd500HumanGate:
    gate_id: str
    applies_to: str
    required: bool
    condition: str
    approval_options: List[str]
    notes: List[str]


# --- Hardcoded minimum gate set ---

_DEFAULT_APPROVAL_OPTIONS = ["approve", "reject", "defer", "request_changes"]

_REQUIRED_GATES: List[Prd500HumanGate] = [
    Prd500HumanGate(
        gate_id="GATE-HIGH-RISK",
        applies_to="HIGH risk windows",
        required=True,
        condition="any HIGH risk task exists",
        approval_options=list(_DEFAULT_APPROVAL_OPTIONS),
        notes=["Blocks execution when any task has risk_level=HIGH"],
    ),
    Prd500HumanGate(
        gate_id="GATE-FROZEN",
        applies_to="FROZEN domains",
        required=True,
        condition="any FROZEN risk task exists",
        approval_options=list(_DEFAULT_APPROVAL_OPTIONS),
        notes=["Blocks execution when any task targets a FROZEN domain"],
    ),
    Prd500HumanGate(
        gate_id="GATE-RUNTIME-INTEGRATION",
        applies_to="runtime integration review",
        required=True,
        condition="any runtime integration task exists",
        approval_options=list(_DEFAULT_APPROVAL_OPTIONS),
        notes=["Required before runtime integration review"],
    ),
    Prd500HumanGate(
        gate_id="GATE-HOOK-IMPLEMENTATION",
        applies_to="hook implementation review",
        required=True,
        condition="any hook implementation task exists",
        approval_options=list(_DEFAULT_APPROVAL_OPTIONS),
        notes=["Required before hook implementation review"],
    ),
    Prd500HumanGate(
        gate_id="GATE-LIVE-EXECUTION",
        applies_to="live execution discussion",
        required=True,
        condition="always blocked",
        approval_options=list(_DEFAULT_APPROVAL_OPTIONS),
        notes=["Always blocked — no live execution without explicit human approval"],
    ),
    Prd500HumanGate(
        gate_id="GATE-PLANNER-AUTONOMOUS",
        applies_to="planner autonomous execution",
        required=True,
        condition="always blocked",
        approval_options=list(_DEFAULT_APPROVAL_OPTIONS),
        notes=["Always blocked — planner must not execute autonomously"],
    ),
]


# --- Builder ---


def build_prd_500_human_gate_pack(backlog: PrdBacklog) -> List[Prd500HumanGate]:
    """Build human gate pack for a backlog.

    Returns the hardcoded minimum gate set. The backlog parameter
    is accepted for future extension but does not alter the output
    in this version — gates are deterministic.
    """
    return list(_REQUIRED_GATES)


# --- Serializers ---


def human_gate_pack_to_dict(gate: Prd500HumanGate) -> Dict[str, object]:
    return {
        "gate_id": gate.gate_id,
        "applies_to": gate.applies_to,
        "required": gate.required,
        "condition": gate.condition,
        "approval_options": list(gate.approval_options),
        "notes": list(gate.notes),
    }


def human_gate_pack_to_markdown(gate: Prd500HumanGate) -> str:
    lines: List[str] = []
    lines.append(f"### {gate.gate_id}")
    lines.append("")
    lines.append(f"- **Applies to:** {gate.applies_to}")
    lines.append(f"- **Required:** {gate.required}")
    lines.append(f"- **Condition:** {gate.condition}")
    lines.append(f"- **Approval options:** {', '.join(gate.approval_options)}")
    if gate.notes:
        lines.append("- **Notes:**")
        for note in gate.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return "\n".join(lines)
