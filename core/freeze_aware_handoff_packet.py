"""T1116 - Freeze-Aware Handoff Packet."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreezeAwareHandoffPacket:
    """Immutable handoff packet.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    from_agent: str
    to_agent: str
    task_id: str
    explicit_files: tuple[str, ...]
    verification_command: str
    notes: str


def build_handoff_packet(
    from_agent: str,
    to_agent: str,
    task_id: str,
    explicit_files: tuple[str, ...] = (),
    verification_command: str = "",
    notes: str = "",
) -> FreezeAwareHandoffPacket:
    """Factory for FreezeAwareHandoffPacket."""
    return FreezeAwareHandoffPacket(
        from_agent=from_agent,
        to_agent=to_agent,
        task_id=task_id,
        explicit_files=tuple(explicit_files),
        verification_command=verification_command,
        notes=notes,
    )
