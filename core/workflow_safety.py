"""Workflow Safety Layer — policy validation for workflow execution.

Pure validation. No system call blocking.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class SafetyViolation:
    rule: str
    severity: Severity
    detail: str
    task_id: str | None = None


# Forbidden patterns in task IDs or descriptions
FORBIDDEN_TASK_PATTERNS = [
    "runtime_integration",
    "planner_integration",
    "live_runner",
    "live_mode",
    "submit_order",
    "cancel_order",
    "flatten_position",
]

# Forbidden workflow modes
FORBIDDEN_MODES = [
    "LIVE_EXECUTION",
    "REAL_TRADING",
    "PLANNER_MODE",
]

# Frozen file patterns (must never be written)
FROZEN_PATTERNS = [
    "live_runner",
    "live_playbook",
    "submit_approved",
    "submit_replayed",
    "run_replay_submit",
    "safe_flatten",
    "run_spot_testnet",
    "run_testnet_order",
    "verify_testnet_repair",
    "replay_shadow",
    "run_controlled",
    "run_daily_shadow",
    "run_next_shadow",
    "run_observation",
    "run_remediation",
    "run_right_breakout",
    "run_shadow_observation",
    "run_shadow_sample",
    "run_shadow_universe",
    "run_signal_testnet",
]

# Valid state transitions (from governance_state)
VALID_TRANSITIONS = {
    "NEW": {"READY", "BLOCKED"},
    "READY": {"RUNNING", "BLOCKED"},
    "RUNNING": {"PASS", "PARTIAL", "FAIL", "BLOCKED"},
    "PASS": {"CLOSED"},
    "PARTIAL": {"CLOSED", "RUNNING"},
    "FAIL": {"CLOSED", "RUNNING"},
    "BLOCKED": {"READY", "RUNNING"},
    "CLOSED": set(),
}


class WorkflowSafetyValidator:
    def __init__(self):
        self.violations: list[SafetyViolation] = []

    def validate_task_id(self, task_id: str) -> list[SafetyViolation]:
        violations = []
        for pattern in FORBIDDEN_TASK_PATTERNS:
            if pattern in task_id.lower():
                v = SafetyViolation(
                    rule="FORBIDDEN_TASK_PATTERN",
                    severity=Severity.CRITICAL,
                    detail=f"Task '{task_id}' contains forbidden pattern '{pattern}'",
                    task_id=task_id,
                )
                violations.append(v)
                self.violations.append(v)
        return violations

    def validate_mode(self, mode: str) -> list[SafetyViolation]:
        violations = []
        if mode in FORBIDDEN_MODES:
            v = SafetyViolation(
                rule="FORBIDDEN_MODE",
                severity=Severity.CRITICAL,
                detail=f"Mode '{mode}' is forbidden",
            )
            violations.append(v)
            self.violations.append(v)
        return violations

    def validate_transition(self, from_state: str, to_state: str, task_id: str) -> list[SafetyViolation]:
        violations = []
        valid_targets = VALID_TRANSITIONS.get(from_state, set())
        if to_state not in valid_targets:
            v = SafetyViolation(
                rule="INVALID_TRANSITION",
                severity=Severity.HIGH,
                detail=f"Invalid transition: {from_state} -> {to_state}",
                task_id=task_id,
            )
            violations.append(v)
            self.violations.append(v)
        return violations

    def validate_frozen_exclusion(self, task_id: str, files: list[str]) -> list[SafetyViolation]:
        violations = []
        for f in files:
            for pattern in FROZEN_PATTERNS:
                if pattern in f:
                    v = SafetyViolation(
                        rule="FROZEN_FILE_ACCESS",
                        severity=Severity.CRITICAL,
                        detail=f"Task '{task_id}' accesses frozen file '{f}'",
                        task_id=task_id,
                    )
                    violations.append(v)
                    self.violations.append(v)
                    break
        return violations

    def validate_workflow(self, workflow_data: dict) -> list[SafetyViolation]:
        violations = []

        # Check mode
        mode = workflow_data.get("mode", "")
        violations.extend(self.validate_mode(mode))

        # Check tasks
        tasks = workflow_data.get("tasks", [])
        for task in tasks:
            task_id = task.get("id", "")
            violations.extend(self.validate_task_id(task_id))

            # Check deps reference valid tasks
            task_ids = {t["id"] for t in tasks}
            for dep in task.get("deps", []):
                if dep not in task_ids:
                    v = SafetyViolation(
                        rule="INVALID_DEPENDENCY",
                        severity=Severity.MEDIUM,
                        detail=f"Task '{task_id}' depends on unknown task '{dep}'",
                        task_id=task_id,
                    )
                    violations.append(v)
                    self.violations.append(v)

        return violations

    def has_critical(self) -> bool:
        return any(v.severity == Severity.CRITICAL for v in self.violations)

    def summary(self) -> dict:
        counts = {}
        for v in self.violations:
            s = v.severity.value
            counts[s] = counts.get(s, 0) + 1
        return {
            "total": len(self.violations),
            "by_severity": counts,
            "has_critical": self.has_critical(),
            "rules_triggered": list(set(v.rule for v in self.violations)),
        }


def validate_workflow_safety(workflow_data: dict) -> dict:
    """Quick validation function."""
    validator = WorkflowSafetyValidator()
    violations = validator.validate_workflow(workflow_data)
    return {
        "safe": len(violations) == 0,
        "violations": [{"rule": v.rule, "severity": v.severity.value, "detail": v.detail} for v in violations],
        "summary": validator.summary(),
    }


def pre_tag_frozen_check(staged_files: list[str]) -> dict:
    """Pre-tag integrity check: verify no frozen files are staged.

    Call this BEFORE creating any git tag to prevent frozen file contamination.

    Args:
        staged_files: List of file paths staged for commit (from git diff --cached --name-only)

    Returns:
        dict with:
            - safe: bool (True if no frozen files staged)
            - violations: list of frozen files found
            - checked: int (number of files checked)
    """
    violations = []
    for f in staged_files:
        for pattern in FROZEN_PATTERNS:
            if pattern in f:
                violations.append({
                    "file": f,
                    "pattern": pattern,
                    "rule": "PRE_TAG_FROZEN_CHECK",
                    "severity": "CRITICAL",
                    "detail": f"Frozen file '{f}' detected in staged files. BLOCKED before tag.",
                })
                break

    return {
        "safe": len(violations) == 0,
        "violations": violations,
        "checked": len(staged_files),
    }
