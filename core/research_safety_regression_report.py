"""Research safety regression report — comprehensive safety verification.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE, SAFETY_FLAGS


def build_safety_regression_report(
    release_hold: str = RELEASE_HOLD_VALUE,
    advisory_only: bool = True,
    human_review_required: bool = True,
    frozen_violations: Tuple[str, ...] = (),
    forbidden_imports: Tuple[str, ...] = (),
    workspace_dirty: bool = False,
    git_add_dot: bool = False,
    seed: int = 424242,
) -> Dict:
    """Build comprehensive safety regression report."""
    flags_correct = (
        release_hold == RELEASE_HOLD_VALUE
        and advisory_only
        and human_review_required
    )

    violations = []
    if release_hold != RELEASE_HOLD_VALUE:
        violations.append(f"release_hold={release_hold}, expected HOLD")
    if not advisory_only:
        violations.append("advisory_only must be True")
    if not human_review_required:
        violations.append("human_review_required must be True")
    if frozen_violations:
        violations.extend(f"FOZEN:{v}" for v in frozen_violations)
    if forbidden_imports:
        violations.extend(f"IMPORT:{v}" for v in forbidden_imports)
    if git_add_dot:
        violations.append("git_add_dot_detected")

    blocks = [v for v in violations if "FOZEN" in v or "IMPORT" in v or "release_hold" in v]

    if blocks:
        verdict = "FAIL"
    elif violations:
        verdict = "PARTIAL"
    else:
        verdict = "PASS"

    return {
        "schema_version": "1.0.0",
        "generated_by": "research_safety_regression",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": release_hold,
        "advisory_only": advisory_only,
        "human_review_required": human_review_required,
        "safety_flags": dict(SAFETY_FLAGS),
        "flags_correct": flags_correct,
        "frozen_violations": list(frozen_violations),
        "forbidden_imports": list(forbidden_imports),
        "workspace_dirty": workspace_dirty,
        "git_add_dot_detected": git_add_dot,
        "violations": violations,
        "warnings": [],
        "hard_blocks": blocks,
        "verdict": verdict,
    }
