"""T851 — Runtime governance read-only verification command plan."""
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyVerificationCommand:
    command_id: str
    command: str
    purpose: str
    required: bool


def build_readonly_verification_command_plan() -> List[RuntimeGovernanceReadOnlyVerificationCommand]:
    """Return deterministic list of read-only verification commands."""
    return [
        RuntimeGovernanceReadOnlyVerificationCommand(
            command_id="readonly-tests",
            command="python3 -m pytest tests/unit/test_runtime_governance_readonly_* -v",
            purpose="Run all read-only layer tests",
            required=True,
        ),
        RuntimeGovernanceReadOnlyVerificationCommand(
            command_id="runtime-governance-tests",
            command="python3 -m pytest tests/unit/test_runtime_governance_* -v",
            purpose="Run all runtime governance tests",
            required=True,
        ),
        RuntimeGovernanceReadOnlyVerificationCommand(
            command_id="governance-failure-tests",
            command="python3 -m pytest tests/unit/test_governance_failure_* -v",
            purpose="Run governance failure taxonomy tests",
            required=True,
        ),
        RuntimeGovernanceReadOnlyVerificationCommand(
            command_id="core-regression",
            command="python3 -m pytest tests/unit/test_execution.py tests/unit/test_risk_manager.py tests/unit/test_order_manager.py tests/unit/test_signal_engine.py -v",
            purpose="Run core regression tests",
            required=True,
        ),
        RuntimeGovernanceReadOnlyVerificationCommand(
            command_id="full-readonly-bundle",
            command="python3 -m pytest tests/unit/test_runtime_governance_readonly_* tests/unit/test_runtime_governance_* tests/unit/test_governance_failure_* -q",
            purpose="Run full readonly + governance bundle",
            required=False,
        ),
    ]


def readonly_verification_command_plan_to_dict(
    commands: List[RuntimeGovernanceReadOnlyVerificationCommand],
) -> List[Dict]:
    """Serialize to list of dicts."""
    return [
        {
            "command_id": c.command_id,
            "command": c.command,
            "purpose": c.purpose,
            "required": c.required,
        }
        for c in commands
    ]


def readonly_verification_command_plan_to_markdown(
    commands: List[RuntimeGovernanceReadOnlyVerificationCommand],
) -> str:
    """Render as deterministic markdown."""
    lines = ["# Runtime Governance Read-Only Verification Command Plan", ""]
    lines.append("| # | Command ID | Command | Purpose | Required |")
    lines.append("|---|------------|---------|---------|----------|")
    for i, c in enumerate(commands, 1):
        req = "yes" if c.required else "no"
        lines.append(f"| {i} | {c.command_id} | `{c.command}` | {c.purpose} | {req} |")
    lines.append("")
    return "\n".join(lines)
