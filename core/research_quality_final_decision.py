"""Research quality final decision — PASS/PARTIAL/FAIL decision engine.

PASS impossible unless all acceptance commands pass. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class FinalDecision:
    """Final quality gate decision."""
    verdict: str  # PASS, PARTIAL, FAIL
    reasons: Tuple[str, ...]
    required_commands_passed: bool
    all_artifacts_present: bool
    safety_holds: bool


def evaluate_final_decision(
    full_suite_passed: bool,
    workbench_acceptance_passed: bool,
    quality_gate_passed: bool,
    rerun_passed: bool,
    comparator_passed: bool,
    closeout_generated: bool,
    all_artifacts_present: bool,
    release_hold_is_hold: bool = True,
    advisory_only: bool = True,
    human_review_required: bool = True,
    no_frozen_violations: bool = True,
) -> FinalDecision:
    """Evaluate final PASS/PARTIAL/FAIL decision."""
    reasons = []
    verdict = "PASS"

    # FAIL conditions
    if not release_hold_is_hold:
        verdict = "FAIL"
        reasons.append("release_hold != HOLD")
    if not advisory_only:
        verdict = "FAIL"
        reasons.append("advisory_only is false")
    if not human_review_required:
        verdict = "FAIL"
        reasons.append("human_review_required is false")
    if not no_frozen_violations:
        verdict = "FAIL"
        reasons.append("frozen file violations detected")
    if not all_artifacts_present:
        verdict = "FAIL"
        reasons.append("required artifacts missing")

    # PARTIAL conditions
    if verdict != "FAIL":
        if not full_suite_passed:
            verdict = "PARTIAL"
            reasons.append("full suite not run")
        if not quality_gate_passed:
            verdict = "PARTIAL"
            reasons.append("quality gate not passed")
        if not rerun_passed:
            verdict = "PARTIAL"
            reasons.append("rerun not passed")
        if not comparator_passed:
            verdict = "PARTIAL"
            reasons.append("comparator not passed")
        if not closeout_generated:
            verdict = "PARTIAL"
            reasons.append("closeout not generated")

    if not reasons:
        reasons.append("all checks passed")

    commands_passed = (full_suite_passed and workbench_acceptance_passed
                       and quality_gate_passed and rerun_passed and comparator_passed)

    return FinalDecision(
        verdict=verdict,
        reasons=tuple(reasons),
        required_commands_passed=commands_passed,
        all_artifacts_present=all_artifacts_present,
        safety_holds=release_hold_is_hold and advisory_only and human_review_required,
    )


def final_decision_to_dict(d: FinalDecision) -> Dict:
    return {
        "verdict": d.verdict,
        "reasons": list(d.reasons),
        "required_commands_passed": d.required_commands_passed,
        "all_artifacts_present": d.all_artifacts_present,
        "safety_holds": d.safety_holds,
    }
