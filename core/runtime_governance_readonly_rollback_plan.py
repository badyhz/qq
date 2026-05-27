"""T845: Runtime governance read-only rollback plan.

Static rollback plan for future read-only implementation.
Pure, deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyRollbackStep:
    step_id: str
    trigger: str
    action: str
    verification: str
    owner: str


def build_readonly_rollback_plan() -> List[RuntimeGovernanceReadOnlyRollbackStep]:
    """Build static rollback plan for read-only governance violations."""
    return [
        RuntimeGovernanceReadOnlyRollbackStep(
            step_id="unexpected_write_detected",
            trigger="unexpected write permission",
            action="halt implementation",
            verification="invariant checker shows no write",
            owner="governance controller",
        ),
        RuntimeGovernanceReadOnlyRollbackStep(
            step_id="network_call_detected",
            trigger="network call detected",
            action="halt implementation",
            verification="invariant checker shows no network",
            owner="governance controller",
        ),
        RuntimeGovernanceReadOnlyRollbackStep(
            step_id="secret_access_detected",
            trigger="secret access detected",
            action="halt implementation",
            verification="invariant checker shows no secret",
            owner="governance controller",
        ),
        RuntimeGovernanceReadOnlyRollbackStep(
            step_id="planner_bypass_detected",
            trigger="planner bypass detected",
            action="halt implementation",
            verification="planner integration frozen",
            owner="governance controller",
        ),
        RuntimeGovernanceReadOnlyRollbackStep(
            step_id="permission_creep_detected",
            trigger="permission creep detected",
            action="revert to last clean state",
            verification="permission envelope clean",
            owner="governance controller",
        ),
    ]


def readonly_rollback_plan_to_dict(
    steps: List[RuntimeGovernanceReadOnlyRollbackStep],
) -> List[Dict]:
    """Convert rollback steps to list of dicts."""
    return [
        {
            "step_id": s.step_id,
            "trigger": s.trigger,
            "action": s.action,
            "verification": s.verification,
            "owner": s.owner,
        }
        for s in steps
    ]


def readonly_rollback_plan_to_markdown(
    steps: List[RuntimeGovernanceReadOnlyRollbackStep],
) -> str:
    """Convert rollback steps to markdown table."""
    lines = [
        "# Runtime Governance Read-Only Rollback Plan",
        "",
        "| step_id | trigger | action | verification | owner |",
        "|---------|---------|--------|--------------|-------|",
    ]
    for s in steps:
        lines.append(
            f"| {s.step_id} | {s.trigger} | {s.action} | {s.verification} | {s.owner} |"
        )
    return "\n".join(lines) + "\n"
