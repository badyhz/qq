"""Network-off execution packet: captures what would execute with network disabled."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ExecutionStep:
    step_id: str
    description: str
    would_execute: bool
    network_required: bool
    submit_required: bool
    credential_required: bool
    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id, "description": self.description,
            "would_execute": self.would_execute, "network_required": self.network_required,
            "submit_required": self.submit_required, "credential_required": self.credential_required,
        }


@dataclass(frozen=True)
class NetworkOffExecutionPacket:
    packet_id: str
    created_at: str
    steps: tuple[ExecutionStep, ...]
    network_off_verdict: str
    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id, "created_at": self.created_at,
            "steps": [s.to_dict() for s in self.steps],
            "network_off_verdict": self.network_off_verdict,
        }


STEPS = (
    ExecutionStep("EXEC_001", "Load config.yaml", True, False, False, False),
    ExecutionStep("EXEC_002", "Initialize logging", True, False, False, False),
    ExecutionStep("EXEC_003", "Load market data feed (mock)", True, False, False, False),
    ExecutionStep("EXEC_004", "Run signal engine", True, False, False, False),
    ExecutionStep("EXEC_005", "Evaluate risk manager", True, False, False, False),
    ExecutionStep("EXEC_006", "Prepare execution packet", True, False, False, False),
    ExecutionStep("EXEC_007", "Gate: real network call", False, True, False, False),
    ExecutionStep("EXEC_008", "Gate: testnet submit", False, False, True, False),
    ExecutionStep("EXEC_009", "Gate: real credentials", False, False, False, True),
    ExecutionStep("EXEC_010", "Write trade log", True, False, False, False),
)


def create_packet() -> NetworkOffExecutionPacket:
    return NetworkOffExecutionPacket(
        packet_id=f"NOE_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        steps=STEPS,
        network_off_verdict="NETWORK_OFF_EXECUTION_PACKET_READY|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_packet(packet: NetworkOffExecutionPacket, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")


def render_report(packet: NetworkOffExecutionPacket) -> str:
    lines = ["# Network-Off Execution Packet", "",
        f"**packet_id={packet.packet_id}**",
        f"**verdict={packet.network_off_verdict}**", "",
        "## Execution Steps", "",
        "| Step | Description | Would Execute | Network | Submit | Credential |",
        "|------|-------------|:---:|:---:|:---:|:---:|"]
    for s in packet.steps:
        lines.append(f"| {s.step_id} | {s.description} | {'Y' if s.would_execute else 'N'} | {'Y' if s.network_required else 'N'} | {'Y' if s.submit_required else 'N'} | {'Y' if s.credential_required else 'N'} |")
    lines.extend(["", "## Conclusion", "",
        "NETWORK_OFF_EXECUTION_PACKET_READY",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
