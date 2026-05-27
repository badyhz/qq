"""T856: Runtime governance read-only batch summary packet.

Pure, deterministic, no I/O, no timestamps, no random.
Summarizes T826-T856 as frozen dataclass packet.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyBatchSummaryPacket:
    task_range: str
    total_tasks: int
    expected_artifacts: int
    final_status: str
    verification_commands: tuple  # frozen requires immutable
    notes: tuple

    def __post_init__(self):
        # Convert lists to tuples for frozen compatibility
        if not isinstance(self.verification_commands, tuple):
            object.__setattr__(self, 'verification_commands', tuple(self.verification_commands))
        if not isinstance(self.notes, tuple):
            object.__setattr__(self, 'notes', tuple(self.notes))


def build_readonly_batch_summary_packet() -> RuntimeGovernanceReadOnlyBatchSummaryPacket:
    return RuntimeGovernanceReadOnlyBatchSummaryPacket(
        task_range="T826-T856",
        total_tasks=31,
        expected_artifacts=93,
        final_status="PASS",
        verification_commands=[
            "python3 -m pytest tests/unit/test_runtime_governance_readonly_* -v",
            "python3 -m pytest tests/unit/test_runtime_governance_* -v",
        ],
        notes=[
            "All read-only design tasks complete.",
            "No live authorization.",
            "Manual review required.",
        ],
    )


def readonly_batch_summary_packet_to_dict(packet: RuntimeGovernanceReadOnlyBatchSummaryPacket) -> Dict:
    return {
        "task_range": packet.task_range,
        "total_tasks": packet.total_tasks,
        "expected_artifacts": packet.expected_artifacts,
        "final_status": packet.final_status,
        "verification_commands": list(packet.verification_commands),
        "notes": list(packet.notes),
    }


def readonly_batch_summary_packet_to_markdown(packet: RuntimeGovernanceReadOnlyBatchSummaryPacket) -> str:
    lines = [
        f"# Runtime Governance Read-Only Batch Summary: {packet.task_range}",
        "",
        f"- **Total tasks:** {packet.total_tasks}",
        f"- **Expected artifacts:** {packet.expected_artifacts}",
        f"- **Final status:** {packet.final_status}",
        "",
        "## Verification Commands",
        "",
    ]
    for cmd in packet.verification_commands:
        lines.append(f"- `{cmd}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in packet.notes:
        lines.append(f"- {note}")
    return "\n".join(lines)
