"""Agent handoff envelope — frozen dataclass for agent task delegation.

T1391 — Pure, frozen, no I/O, no network, no random, no timestamps, no env reads.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class AgentHandoffEnvelope:
    """Envelope describing an agent handoff mission and its constraints."""

    envelope_id: str
    mission_summary: str
    allowed_scope: Tuple[str, ...]
    forbidden_paths: Tuple[str, ...]
    test_commands: Tuple[str, ...]
    commit_rules: Tuple[str, ...]
    safety_constraints: Tuple[str, ...]
