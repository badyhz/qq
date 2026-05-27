"""Agent handoff commit rule — frozen dataclass for commit constraints.

T1394 — Pure, frozen, no I/O, no network, no random, no timestamps, no env reads.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentHandoffCommitRule:
    """Commit rule governing how an agent may commit changes."""

    rule_id: str
    pattern: str
    description: str
    required: bool
