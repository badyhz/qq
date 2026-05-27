"""Read-only hook rollout — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RolloutHold:
    hold_id: str
    hold_active: bool
    scope: str
    reasons: List[str]
    release_conditions: List[str]
    final_verdict: str  # "HOLD"


@dataclass(frozen=True)
class RollbackStep:
    step_id: str
    order: int
    description: str
    reversible: bool


def build_rollout_hold() -> RolloutHold:
    return RolloutHold(
        hold_id="hold_read_only_hook",
        hold_active=True,
        scope="read_only_hook_layer",
        reasons=[
            "Pending review checklist approval",
            "Invariant coverage not yet verified in integration",
            "Threat model acceptance pending",
        ],
        release_conditions=[
            "All review checklist items checked",
            "Regression matrix passes 100%",
            "Threat model all mitigations confirmed",
        ],
        final_verdict="HOLD",
    )


def build_rollback_plan() -> List[RollbackStep]:
    return [
        RollbackStep("rb_01", 1, "Remove read_only_hook_* imports from consumers", True),
        RollbackStep("rb_02", 2, "Delete all read_only_hook_*.py files from core/", True),
        RollbackStep("rb_03", 3, "Remove test files referencing read_only_hook", True),
        RollbackStep("rb_04", 4, "Update CLAUDE.md to remove hook layer references", True),
        RollbackStep("rb_05", 5, "Verify no dangling imports remain", True),
    ]


def rollout_hold_to_dict(rh: RolloutHold) -> dict:
    return {
        "hold_id": rh.hold_id,
        "hold_active": rh.hold_active,
        "scope": rh.scope,
        "reasons": list(rh.reasons),
        "release_conditions": list(rh.release_conditions),
        "final_verdict": rh.final_verdict,
    }


def rollback_step_to_dict(rs: RollbackStep) -> dict:
    return {
        "step_id": rs.step_id,
        "order": rs.order,
        "description": rs.description,
        "reversible": rs.reversible,
    }
