"""T1335 - Human approval command transcript."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalCommandTranscript:
    """Immutable record of commands executed and their outputs during approval."""

    transcript_id: str
    commands: tuple[str, ...]
    outputs: tuple[str, ...]
    verified: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "transcript_id": self.transcript_id,
            "commands": list(self.commands),
            "outputs": list(self.outputs),
            "verified": self.verified,
        }

    def command_count(self) -> int:
        return len(self.commands)

    def has_output_for(self, index: int) -> bool:
        return 0 <= index < len(self.outputs)
