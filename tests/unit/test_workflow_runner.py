"""Tests for Workflow Runner."""
from __future__ import annotations

import pytest

from core.workflow_runner import WorkflowRunner


def test_runner_creation():
    runner = WorkflowRunner("SAFE_READONLY_AUDIT")
    assert runner.template["name"] == "SAFE_READONLY_AUDIT"


def test_build_from_tasks():
    runner = WorkflowRunner("GUARD_INJECTION_BATCH")
    runner.build_from_tasks([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": ["T1"]},
    ])
    assert "T1" in runner.factory.tasks
    assert "T2" in runner.factory.tasks


def test_build_from_template():
    runner = WorkflowRunner("SAFE_READONLY_AUDIT")
    runner.build_from_template()
    assert len(runner.factory.tasks) == 5


def test_plan():
    runner = WorkflowRunner("GUARD_INJECTION_BATCH")
    runner.build_from_template()
    plan = runner.plan()
    assert "waves" in plan
    assert "ready" in plan
    assert "blocked" in plan
    assert plan["total_tasks"] == 5


def test_simulate_execution():
    runner = WorkflowRunner("GUARD_INJECTION_BATCH")
    runner.build_from_template()
    results = runner.simulate_execution()
    assert len(results) == 5
    assert all(r["status"] == "PASS" for r in results)


def test_summary():
    runner = WorkflowRunner("DOCS_SYNC_WAVE")
    runner.build_from_template()
    summary = runner.summary()
    assert summary["tasks_total"] == 5
    assert summary["tasks_executed"] == 5


def test_no_tasks_raises():
    runner = WorkflowRunner("SAFE_READONLY_AUDIT")
    with pytest.raises(RuntimeError, match="No tasks built"):
        runner.plan()


def test_closeout_runner():
    runner = WorkflowRunner("ENGINEERING_CLOSEOUT")
    runner.build_from_template()
    plan = runner.plan()
    assert plan["mode"] == "CLOSEOUT_MODE"
    assert plan["total_tasks"] == 7


def test_custom_tasks():
    runner = WorkflowRunner("SAFE_READONLY_AUDIT")
    runner.build_from_tasks([
        {"id": "A", "deps": []},
        {"id": "B", "deps": ["A"]},
        {"id": "C", "deps": ["A"]},
        {"id": "D", "deps": ["B", "C"]},
    ])
    results = runner.simulate_execution()
    assert len(results) == 4


def test_state_transitions():
    runner = WorkflowRunner("GUARD_INJECTION_BATCH")
    runner.build_from_tasks([{"id": "T1", "deps": []}])
    runner.simulate_execution()

    task_state = runner.state_machine.tasks["T1"]
    assert task_state.state.value == "PASS"
    assert len(task_state.history) == 3  # READY -> RUNNING -> PASS
