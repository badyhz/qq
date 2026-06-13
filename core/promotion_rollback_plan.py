"""T17501 — Promotion Rollback Plan Generator.

Pure deterministic. No I/O. No network.
Generates rollback plan for shadow-to-testnet promotion.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"


@dataclass(frozen=True)
class RollbackStep:
    """Single rollback step."""
    step_id: str
    order: int
    action: str
    description: str
    simulation_only: bool

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "order": self.order,
            "action": self.action,
            "description": self.description,
            "simulation_only": self.simulation_only,
        }


@dataclass(frozen=True)
class RollbackPlan:
    """Complete rollback plan."""
    plan_id: str
    steps: list[RollbackStep]
    total_steps: int
    trigger_conditions: list[str]
    simulation_only: bool
    release_hold: str

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": self.total_steps,
            "trigger_conditions": self.trigger_conditions,
            "simulation_only": self.simulation_only,
            "release_hold": self.release_hold,
        }


def build_rollback_plan(release_hold: str = RELEASE_HOLD_REQUIRED) -> RollbackPlan:
    """Build rollback plan for shadow-to-testnet promotion."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    steps = [
        RollbackStep(step_id="rollback_1", order=1, action="REVERT_TO_SHADOW_ONLY",
                     description="Revert system mode to SHADOW_ONLY", simulation_only=True),
        RollbackStep(step_id="rollback_2", order=2, action="DISABLE_TESTNET_DRY_RUN",
                     description="Disable testnet dry-run orchestrator", simulation_only=True),
        RollbackStep(step_id="rollback_3", order=3, action="RE_ENABLE_NO_SUBMIT_GUARD",
                     description="Re-enable no-submit execution guard", simulation_only=True),
        RollbackStep(step_id="rollback_4", order=4, action="RESTORE_FROZEN_STATE",
                     description="Restore all frozen files to pre-promotion state", simulation_only=True),
        RollbackStep(step_id="rollback_5", order=5, action="GENERATE_ROLLBACK_REPORT",
                     description="Generate rollback evidence report", simulation_only=True),
    ]

    return RollbackPlan(
        plan_id="shadow_to_testnet_rollback_plan",
        steps=steps,
        total_steps=len(steps),
        trigger_conditions=[
            "testnet_dry_run_submits_real_order",
            "no_submit_guard_bypassed",
            "critical_blocker_detected",
            "stability_score_below_threshold",
            "human_operator_requests_rollback",
        ],
        simulation_only=True,
        release_hold=release_hold,
    )


def compute_rollback_hash(plan: RollbackPlan) -> str:
    raw = json.dumps(plan.to_dict(), sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_rollback_markdown(plan: RollbackPlan) -> str:
    lines = [
        "# Shadow-to-Testnet Rollback Plan",
        "",
        f"**Plan ID:** {plan.plan_id}",
        f"**Total steps:** {plan.total_steps}",
        f"**simulation_only:** {plan.simulation_only}",
        f"**release_hold:** {plan.release_hold}",
        "",
        "## Trigger Conditions",
        "",
    ]
    for tc in plan.trigger_conditions:
        lines.append(f"- {tc}")

    lines.append("")
    lines.append("## Rollback Steps")
    lines.append("")

    for step in plan.steps:
        lines.append(f"### Step {step.order}: {step.action}")
        lines.append("")
        lines.append(f"- **step_id:** {step.step_id}")
        lines.append(f"- **description:** {step.description}")
        lines.append(f"- **simulation_only:** {step.simulation_only}")
        lines.append("")

    lines.append("---")
    lines.append("ROLLBACK PLAN. SIMULATION ONLY. NO REAL ACTIONS.")
    lines.append("")

    return "\n".join(lines)


def write_json(plan: RollbackPlan, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")


def write_manifest(plan: RollbackPlan, out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "plan_id": plan.plan_id,
        "total_steps": plan.total_steps,
        "release_hold": release_hold,
        "simulation_only": True,
        "rollback_hash": compute_rollback_hash(plan),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(plan: RollbackPlan, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_rollback_markdown(plan), encoding="utf-8")
