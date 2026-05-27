"""T835: Runtime governance read-only regression packet.

Pure, deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyRegressionPacket:
    title: str
    scenario_count: int
    scenario_pass_count: int
    scenario_fail_count: int
    side_effect_verdict: str
    manifest_verdict: str
    final_verdict: str  # PASS / FAIL
    notes: Tuple[str, ...] = field(default_factory=tuple)  # frozen-safe


def _compute_verdict(
    scenario_fail_count: int,
    side_effect_verdict: str,
    manifest_verdict: str,
) -> str:
    if scenario_fail_count == 0 and side_effect_verdict == "PASS" and manifest_verdict == "PASS":
        return "PASS"
    return "FAIL"


def build_readonly_regression_packet(
    title: str = "Read-Only Regression Packet",
    scenario_count: int = 6,
    scenario_pass_count: int = 6,
    scenario_fail_count: int = 0,
    side_effect_verdict: str = "PASS",
    manifest_verdict: str = "PASS",
    notes: Optional[List[str]] = None,
) -> RuntimeGovernanceReadOnlyRegressionPacket:
    final = _compute_verdict(scenario_fail_count, side_effect_verdict, manifest_verdict)
    return RuntimeGovernanceReadOnlyRegressionPacket(
        title=title,
        scenario_count=scenario_count,
        scenario_pass_count=scenario_pass_count,
        scenario_fail_count=scenario_fail_count,
        side_effect_verdict=side_effect_verdict,
        manifest_verdict=manifest_verdict,
        final_verdict=final,
        notes=tuple(notes) if notes else (),
    )


def readonly_regression_packet_to_dict(
    packet: RuntimeGovernanceReadOnlyRegressionPacket,
) -> Dict:
    return {
        "title": packet.title,
        "scenario_count": packet.scenario_count,
        "scenario_pass_count": packet.scenario_pass_count,
        "scenario_fail_count": packet.scenario_fail_count,
        "side_effect_verdict": packet.side_effect_verdict,
        "manifest_verdict": packet.manifest_verdict,
        "final_verdict": packet.final_verdict,
        "notes": list(packet.notes),
    }


def readonly_regression_packet_to_markdown(
    packet: RuntimeGovernanceReadOnlyRegressionPacket,
) -> str:
    lines = [
        f"# {packet.title}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Scenario Count | {packet.scenario_count} |",
        f"| Scenario Pass | {packet.scenario_pass_count} |",
        f"| Scenario Fail | {packet.scenario_fail_count} |",
        f"| Side-Effect Verdict | {packet.side_effect_verdict} |",
        f"| Manifest Verdict | {packet.manifest_verdict} |",
        f"| **Final Verdict** | **{packet.final_verdict}** |",
    ]
    if packet.notes:
        lines.append("")
        lines.append("## Notes")
        for note in packet.notes:
            lines.append(f"- {note}")
    return "\n".join(lines)
