"""PRD acceptance command registry.

Static registry of safe verification commands for PRD control-plane.
Pure, deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PrdAcceptanceCommand:
    """A single safe verification command."""

    command_id: str
    command: str
    purpose: str
    required: bool
    safe_for_agent: bool


def build_prd_acceptance_command_registry() -> List[PrdAcceptanceCommand]:
    """Return the full list of PRD acceptance commands."""
    return [
        PrdAcceptanceCommand(
            command_id="prd-control-plane",
            command="python3 -m pytest tests/unit/test_dev_prd_control_plane.py -q",
            purpose="Run PRD control plane tests",
            required=True,
            safe_for_agent=True,
        ),
        PrdAcceptanceCommand(
            command_id="readonly-glob",
            command="python3 -m pytest tests/unit/test_runtime_governance_readonly_* -q",
            purpose="Run readonly layer tests",
            required=True,
            safe_for_agent=True,
        ),
        PrdAcceptanceCommand(
            command_id="runtime-governance-glob",
            command="python3 -m pytest tests/unit/test_runtime_governance_* -q",
            purpose="Run runtime governance tests",
            required=True,
            safe_for_agent=True,
        ),
        PrdAcceptanceCommand(
            command_id="governance-failure-glob",
            command="python3 -m pytest tests/unit/test_governance_failure_* -q",
            purpose="Run governance failure tests",
            required=True,
            safe_for_agent=True,
        ),
        PrdAcceptanceCommand(
            command_id="order-manager",
            command="python3 -m pytest tests/unit/test_order_manager.py -q",
            purpose="Run order manager tests",
            required=True,
            safe_for_agent=True,
        ),
        PrdAcceptanceCommand(
            command_id="git-status",
            command="git status --short",
            purpose="Check working tree status",
            required=False,
            safe_for_agent=True,
        ),
        PrdAcceptanceCommand(
            command_id="git-log",
            command="git log --oneline -40",
            purpose="View recent commits",
            required=False,
            safe_for_agent=True,
        ),
    ]


def acceptance_command_registry_to_dict(
    commands: List[PrdAcceptanceCommand],
) -> List[Dict]:
    """Convert registry to list of dicts."""
    return [
        {
            "command_id": c.command_id,
            "command": c.command,
            "purpose": c.purpose,
            "required": c.required,
            "safe_for_agent": c.safe_for_agent,
        }
        for c in commands
    ]


def acceptance_command_registry_to_markdown(
    commands: List[PrdAcceptanceCommand],
) -> str:
    """Render registry as a markdown table."""
    lines = [
        "| command_id | command | purpose | required | safe_for_agent |",
        "|---|---|---|---|---|",
    ]
    for c in commands:
        lines.append(
            f"| {c.command_id} | `{c.command}` | {c.purpose} "
            f"| {c.required} | {c.safe_for_agent} |"
        )
    return "\n".join(lines)


def summarize_acceptance_command_registry(
    commands: List[PrdAcceptanceCommand],
) -> Dict:
    """Return summary stats for the registry."""
    return {
        "total": len(commands),
        "required": sum(1 for c in commands if c.required),
        "optional": sum(1 for c in commands if not c.required),
        "safe_for_agent": sum(1 for c in commands if c.safe_for_agent),
        "command_ids": [c.command_id for c in commands],
    }
