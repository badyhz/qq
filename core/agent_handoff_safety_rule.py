"""Agent handoff safety rule — frozen dataclass for safety constraints.

T1392 — Pure, frozen, no I/O, no network, no random, no timestamps, no env reads.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentHandoffSafetyRule:
    """Safety rule governing an agent handoff."""

    rule_id: str
    rule_type: str  # FORBIDDEN_PATH / FORBIDDEN_ACTION / REQUIRED_CHECK
    description: str
    severity: str  # CRITICAL / WARNING
