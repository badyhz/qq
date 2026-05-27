from __future__ import annotations

from core.no_submit_release_gate import NoSubmitReleaseGate
from core.no_submit_invariant import NoSubmitInvariant
from core.no_submit_denied_operation import NoSubmitDeniedOperation
from core.no_submit_release_gate_verdict import NoSubmitReleaseGateVerdict


def render_no_submit_gate_md(gate: NoSubmitReleaseGate) -> str:
    """Render a NoSubmitReleaseGate as markdown."""
    lines = ("# No Submit Release Gate", "")
    lines += (f"- **Gate ID:** {gate.gate_id}",)
    lines += (f"- **Verdict:** {gate.verdict}",)
    if gate.invariants:
        lines += ("", "## Invariants",)
        for inv in gate.invariants:
            lines += (f"- {inv}",)
    if gate.denied_operations:
        lines += ("", "## Denied Operations",)
        for op in gate.denied_operations:
            lines += (f"- {op}",)
    return "\n".join(lines)


def render_no_submit_invariant_md(invariant: NoSubmitInvariant) -> str:
    """Render a NoSubmitInvariant as markdown."""
    lines = ("# No Submit Invariant", "")
    lines += (f"- **ID:** {invariant.invariant_id}",)
    lines += (f"- **Description:** {invariant.description}",)
    lines += (f"- **Check function:** {invariant.check_function_name}",)
    return "\n".join(lines)


def render_no_submit_denied_op_md(op: NoSubmitDeniedOperation) -> str:
    """Render a NoSubmitDeniedOperation as markdown."""
    lines = ("# No Submit Denied Operation", "")
    lines += (f"- **Operation:** {op.operation}",)
    lines += (f"- **Category:** {op.category}",)
    lines += (f"- **Severity:** {op.severity}",)
    lines += (f"- **Description:** {op.description}",)
    return "\n".join(lines)


def render_no_submit_verdict_md(verdict: NoSubmitReleaseGateVerdict) -> str:
    """Render a NoSubmitReleaseGateVerdict as markdown."""
    lines = ("# No Submit Release Gate Verdict", "")
    lines += (f"- **Verdict:** {verdict.verdict}",)
    lines += (f"- **Notes:** {verdict.notes}",)
    if verdict.invariant_violations:
        lines += ("", "## Invariant Violations",)
        for v in verdict.invariant_violations:
            lines += (f"- {v}",)
    if verdict.denied_op_attempts:
        lines += ("", "## Denied Operation Attempts",)
        for d in verdict.denied_op_attempts:
            lines += (f"- {d}",)
    return "\n".join(lines)
