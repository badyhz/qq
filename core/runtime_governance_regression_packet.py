"""Runtime governance regression packet — snapshot regression for governance rules.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# Default scenario IDs
_DEFAULT_SCENARIO_IDS = tuple(f"S{n}" for n in range(1, 21))
_DEFAULT_SCENARIO_COUNT = len(_DEFAULT_SCENARIO_IDS)


@dataclass(frozen=True)
class RuntimeGovernanceRegressionPacket:
    """Immutable regression packet for runtime governance.

    Fields consumed by readiness_score:
      final_verdict, manifest_summary, scenario_fail_count,
      scenario_count, scenario_pass_count, invariant_summary, notes.
    """

    title: str
    final_verdict: str  # "PASS" / "FAIL" / "BLOCKED"
    scenario_count: int
    scenario_pass_count: int
    scenario_fail_count: int
    invariant_summary: Dict[str, Any]  # {"errors": int, "warnings": int, "total": int, ...}
    manifest_summary: Dict[str, Any]  # {"verdict": str, ...}
    notes: List[str] = field(default_factory=list)


# ── builder ───────────────────────────────────────────────────────────


def build_runtime_governance_regression_packet(
    *,
    title: str = "Runtime Governance Regression Packet",
    final_verdict: str = "PASS",
    scenario_count: int | None = None,
    scenario_pass_count: int | None = None,
    scenario_fail_count: int = 0,
    invariant_summary: Dict[str, Any] | None = None,
    manifest_summary: Dict[str, Any] | None = None,
    notes: List[str] | None = None,
) -> RuntimeGovernanceRegressionPacket:
    """Build regression packet. Pure. No I/O.

    Defaults produce a passing packet with all scenarios passing.
    """
    eff_scenario_count = scenario_count if scenario_count is not None else _DEFAULT_SCENARIO_COUNT
    eff_scenario_pass_count = scenario_pass_count if scenario_pass_count is not None else eff_scenario_count

    return RuntimeGovernanceRegressionPacket(
        title=title,
        final_verdict=final_verdict,
        scenario_count=eff_scenario_count,
        scenario_pass_count=eff_scenario_pass_count,
        scenario_fail_count=scenario_fail_count,
        invariant_summary=dict(invariant_summary) if invariant_summary else {"errors": 0, "warnings": 0, "total": 0},
        manifest_summary=dict(manifest_summary) if manifest_summary else {"verdict": "PASS"},
        notes=list(notes) if notes else [],
    )


# ── serialization ─────────────────────────────────────────────────────


def runtime_regression_packet_to_dict(packet: RuntimeGovernanceRegressionPacket) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "title": packet.title,
        "final_verdict": packet.final_verdict,
        "scenario_count": packet.scenario_count,
        "scenario_pass_count": packet.scenario_pass_count,
        "scenario_fail_count": packet.scenario_fail_count,
        "invariant_summary": dict(packet.invariant_summary),
        "manifest_summary": dict(packet.manifest_summary),
        "notes": list(packet.notes),
    }


def runtime_regression_packet_to_markdown(packet: RuntimeGovernanceRegressionPacket) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines: List[str] = [f"# {packet.title}", ""]
    lines.append(f"**Final Verdict:** {packet.final_verdict}")
    lines.append("")
    lines.append("## Scenario Evaluations")
    lines.append("")
    lines.append(f"- **Total:** {packet.scenario_count}")
    lines.append(f"- **Pass:** {packet.scenario_pass_count}")
    lines.append(f"- **Fail:** {packet.scenario_fail_count}")
    lines.append("")
    lines.append("## Invariant Summary")
    lines.append("")
    for k, v in packet.invariant_summary.items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")
    lines.append("## Manifest Summary")
    lines.append("")
    for k, v in packet.manifest_summary.items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")
    if packet.notes:
        lines.append("## Notes")
        lines.append("")
        for note in packet.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
