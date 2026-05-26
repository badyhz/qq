"""Tests for Workflow Safety Layer."""
from __future__ import annotations

from core.workflow_safety import (
    FROZEN_PATTERNS,
    FORBIDDEN_MODES,
    FORBIDDEN_TASK_PATTERNS,
    Severity,
    WorkflowSafetyValidator,
    validate_workflow_safety,
)


def test_validator_creation():
    v = WorkflowSafetyValidator()
    assert v.violations == []


def test_valid_task_id():
    v = WorkflowSafetyValidator()
    violations = v.validate_task_id("inject_scripts")
    assert len(violations) == 0


def test_forbidden_task_id():
    v = WorkflowSafetyValidator()
    violations = v.validate_task_id("runtime_integration_task")
    assert len(violations) > 0
    assert violations[0].severity == Severity.CRITICAL


def test_valid_mode():
    v = WorkflowSafetyValidator()
    violations = v.validate_mode("DAG")
    assert len(violations) == 0


def test_forbidden_mode():
    v = WorkflowSafetyValidator()
    violations = v.validate_mode("LIVE_EXECUTION")
    assert len(violations) > 0
    assert violations[0].severity == Severity.CRITICAL


def test_valid_transition():
    v = WorkflowSafetyValidator()
    violations = v.validate_transition("NEW", "READY", "T1")
    assert len(violations) == 0


def test_invalid_transition():
    v = WorkflowSafetyValidator()
    violations = v.validate_transition("NEW", "PASS", "T1")
    assert len(violations) > 0
    assert violations[0].severity == Severity.HIGH


def test_frozen_exclusion_clean():
    v = WorkflowSafetyValidator()
    violations = v.validate_frozen_exclusion("T1", ["script_a.py", "script_b.py"])
    assert len(violations) == 0


def test_frozen_exclusion_violation():
    v = WorkflowSafetyValidator()
    violations = v.validate_frozen_exclusion("T1", ["live_runner.py"])
    assert len(violations) > 0
    assert violations[0].severity == Severity.CRITICAL


def test_validate_workflow_clean():
    workflow = {
        "mode": "DAG",
        "tasks": [
            {"id": "T1", "deps": []},
            {"id": "T2", "deps": ["T1"]},
        ],
    }
    result = validate_workflow_safety(workflow)
    assert result["safe"]


def test_validate_workflow_forbidden_mode():
    workflow = {
        "mode": "LIVE_EXECUTION",
        "tasks": [{"id": "T1", "deps": []}],
    }
    result = validate_workflow_safety(workflow)
    assert not result["safe"]


def test_validate_workflow_forbidden_task():
    workflow = {
        "mode": "DAG",
        "tasks": [{"id": "runtime_integration_task", "deps": []}],
    }
    result = validate_workflow_safety(workflow)
    assert not result["safe"]


def test_validate_workflow_invalid_dep():
    workflow = {
        "mode": "DAG",
        "tasks": [{"id": "T1", "deps": ["NONEXISTENT"]}],
    }
    result = validate_workflow_safety(workflow)
    assert not result["safe"]


def test_summary():
    v = WorkflowSafetyValidator()
    v.validate_task_id("runtime_integration")
    v.validate_mode("LIVE_EXECUTION")
    summary = v.summary()
    assert summary["total"] == 2
    assert summary["has_critical"]


def test_has_critical():
    v = WorkflowSafetyValidator()
    assert not v.has_critical()
    v.validate_task_id("runtime_integration")
    assert v.has_critical()


def test_all_forbidden_patterns_documented():
    assert len(FORBIDDEN_TASK_PATTERNS) > 0
    assert "runtime_integration" in FORBIDDEN_TASK_PATTERNS
    assert "planner_integration" in FORBIDDEN_TASK_PATTERNS


def test_all_frozen_patterns_documented():
    assert len(FROZEN_PATTERNS) == 20
    assert "live_runner" in FROZEN_PATTERNS
