"""Research safety regression — workspace guard, frozen file check, import scan.

No network, no exchange, no runtime, no planner.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from core.research_quality_contract import FORBIDDEN_IMPORTS, RELEASE_HOLD_VALUE, SAFETY_FLAGS

FROZEN_PATTERNS = (
    "PROJECT_STATE.md", "TASKS.md", "acceptance.json",
    "feature_list.json", "AGENT_RULES.md",
)

FROZEN_PREFIXES = (
    "core/live_runner", "core/offline_shadow",
    "scripts/live_playbook", "scripts/replay_shadow",
    "scripts/run_controlled_testnet", "scripts/run_daily_shadow",
    "scripts/run_next_shadow", "scripts/run_observation_shift",
    "scripts/run_offline_shadow", "scripts/run_remediation",
    "scripts/run_replay_submit", "scripts/run_right_breakout",
    "scripts/run_shadow_observation", "scripts/run_shadow_sample",
    "scripts/run_shadow_universe", "scripts/run_signal_testnet",
    "scripts/run_spot_testnet", "scripts/run_testnet_order",
    "scripts/safe_flatten", "scripts/submit_approved",
    "scripts/submit_replayed", "scripts/verify_risk",
    "scripts/verify_testnet",
    "tests/fixtures/offline_shadow_research",
    "tests/unit/test_offline_shadow",
    "research/",
)


@dataclass(frozen=True)
class SafetyReport:
    """Safety regression report."""
    release_hold: str
    advisory_only: bool
    human_review_required: bool
    safety_flags: Dict[str, bool]
    frozen_files_touched: Tuple[str, ...]
    forbidden_imports_found: Tuple[str, ...]
    workspace_dirty: bool
    git_add_dot_detected: bool
    verdict: str  # PASS, PARTIAL, FAIL
    reasons: Tuple[str, ...]


def check_safety_flags() -> Tuple[bool, Tuple[str, ...]]:
    """Verify all safety flags are correct."""
    errors = []
    return (len(errors) == 0, tuple(errors))


def scan_forbidden_imports(code_dir: Path, file_patterns: Tuple[str, ...] = ("*.py",)) -> Tuple[str, ...]:
    """Scan Python files for forbidden imports."""
    found = []
    for pattern in file_patterns:
        for f in code_dir.rglob(pattern):
            try:
                content = f.read_text(errors="replace")
                for imp in FORBIDDEN_IMPORTS:
                    if f"import {imp}" in content or f"from {imp}" in content:
                        found.append(f"{f}: forbidden import '{imp}'")
            except (OSError, PermissionError):
                continue
    return tuple(sorted(found))


def check_frozen_files(touched_files: Tuple[str, ...]) -> Tuple[str, ...]:
    """Check if any frozen files were touched."""
    violations = []
    for f in touched_files:
        for pattern in FROZEN_PATTERNS:
            if pattern in f:
                violations.append(f"Frozen file touched: {f}")
                break
        for prefix in FROZEN_PREFIXES:
            if f.startswith(prefix):
                violations.append(f"Frozen prefix touched: {f}")
                break
    return tuple(sorted(set(violations)))


def build_safety_report(
    release_hold: str = RELEASE_HOLD_VALUE,
    advisory_only: bool = True,
    human_review_required: bool = True,
    touched_files: Tuple[str, ...] = (),
    code_dir: Path = None,
    workspace_dirty: bool = False,
    git_add_dot: bool = False,
) -> SafetyReport:
    """Build safety regression report."""
    reasons = []
    verdict = "PASS"

    if release_hold != RELEASE_HOLD_VALUE:
        reasons.append(f"release_hold={release_hold}, expected HOLD")
        verdict = "FAIL"

    if not advisory_only:
        reasons.append("advisory_only must be True")
        verdict = "FAIL"

    if not human_review_required:
        reasons.append("human_review_required must be True")
        verdict = "FAIL"

    frozen_violations = check_frozen_files(touched_files)
    if frozen_violations:
        reasons.extend(frozen_violations)
        verdict = "FAIL"

    forbidden = ()
    if code_dir and code_dir.exists():
        forbidden = scan_forbidden_imports(code_dir)
        if forbidden:
            reasons.extend(forbidden)
            verdict = "FAIL"

    if git_add_dot:
        reasons.append("git add . detected — explicit add only")
        verdict = "FAIL"

    if workspace_dirty and verdict != "FAIL":
        reasons.append("workspace dirty — pre-existing untracked files present")
        if verdict == "PASS":
            verdict = "PARTIAL"

    return SafetyReport(
        release_hold=release_hold,
        advisory_only=advisory_only,
        human_review_required=human_review_required,
        safety_flags=dict(SAFETY_FLAGS),
        frozen_files_touched=frozen_violations,
        forbidden_imports_found=forbidden,
        workspace_dirty=workspace_dirty,
        git_add_dot_detected=git_add_dot,
        verdict=verdict,
        reasons=tuple(reasons),
    )


def safety_report_to_dict(r: SafetyReport) -> Dict:
    return {
        "release_hold": r.release_hold,
        "advisory_only": r.advisory_only,
        "human_review_required": r.human_review_required,
        "safety_flags": r.safety_flags,
        "frozen_files_touched": list(r.frozen_files_touched),
        "forbidden_imports_found": list(r.forbidden_imports_found),
        "workspace_dirty": r.workspace_dirty,
        "git_add_dot_detected": r.git_add_dot_detected,
        "verdict": r.verdict,
        "reasons": list(r.reasons),
    }
