"""Agent handoff test spec — frozen dataclass for test requirements.

T1393 — Pure, frozen, no I/O, no network, no random, no timestamps, no env reads.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentHandoffTestSpec:
    """Test specification required for agent handoff validation."""

    spec_id: str
    test_command: str
    expected_result: str
    timeout_seconds: int
    mandatory: bool
