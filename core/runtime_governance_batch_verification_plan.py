"""T823 — Runtime governance batch verification plan."""
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationCommand:
    command_id: str
    command: str
    purpose: str
    required: bool


def build_runtime_governance_batch_verification_plan() -> list:
    """Return list of VerificationCommand. Deterministic."""
    return [
        VerificationCommand(
            command_id="runtime_governance_tests",
            command="python3 -m pytest tests/unit/test_runtime_governance_*.py -q",
            purpose="runtime governance tests",
            required=True,
        ),
        VerificationCommand(
            command_id="governance_failure_tests",
            command="python3 -m pytest tests/unit/test_governance_failure_*.py -q",
            purpose="governance failure tests",
            required=True,
        ),
        VerificationCommand(
            command_id="core_regression",
            command="python3 -m pytest tests/unit/test_adapter_safety.py tests/unit/test_workflow_safety.py tests/unit/test_governance_state.py -q",
            purpose="core regression",
            required=True,
        ),
        VerificationCommand(
            command_id="git_status",
            command="git status --short",
            purpose="check uncommitted changes",
            required=True,
        ),
        VerificationCommand(
            command_id="no_large_log",
            command="echo 'Do not read full CSV/JSONL/log files'",
            purpose="reminder",
            required=True,
        ),
    ]


def verification_plan_to_dict(plan) -> list:
    """Serialize to list of dicts."""
    return [
        {
            "command_id": c.command_id,
            "command": c.command,
            "purpose": c.purpose,
            "required": c.required,
        }
        for c in plan
    ]


def verification_plan_to_markdown(plan) -> str:
    """Render as deterministic markdown."""
    lines = ["# Runtime Governance Batch Verification Plan", ""]
    lines.append("| # | Command ID | Command | Purpose | Required |")
    lines.append("|---|------------|---------|---------|----------|")
    for i, c in enumerate(plan, 1):
        req = "yes" if c.required else "no"
        lines.append(f"| {i} | {c.command_id} | `{c.command}` | {c.purpose} | {req} |")
    lines.append("")
    return "\n".join(lines)
