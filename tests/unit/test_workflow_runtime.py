"""Tests for WorkflowRuntime."""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.workflow_runtime import WorkflowRuntime


def test_runtime_creation():
    rt = WorkflowRuntime(max_workers=3, mode="DAG")
    assert rt.is_complete()  # no tasks loaded = trivially complete


def test_load_workflow_valid():
    rt = WorkflowRuntime()
    result = rt.load_workflow([{"id": "T1", "deps": []}])
    assert result["valid"] is True
    assert result["task_count"] == 1


def test_load_workflow_forbidden_task_rejected():
    rt = WorkflowRuntime()
    result = rt.load_workflow([{"id": "submit_order_test", "deps": []}])
    assert result["valid"] is False
    assert "violations" in result


def test_run_completes_all_tasks():
    rt = WorkflowRuntime(max_workers=3)
    rt.load_workflow([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": []},
        {"id": "T3", "deps": ["T1"]},
    ])
    result = rt.run()
    assert result["is_complete"] is True
    assert result["completed"] == 3


def test_run_step_advances_one_wave():
    rt = WorkflowRuntime(max_workers=5)
    rt.load_workflow([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": []},
        {"id": "T3", "deps": ["T1", "T2"]},
    ])
    step1 = rt.run_step()
    assert len(step1["assigned"]) == 2  # T1 and T2 are independent
    assert not rt.is_complete()  # T3 not done yet
    step2 = rt.run_step()
    assert len(step2["assigned"]) == 1  # T3 should be ready now
    assert rt.is_complete()


def test_is_complete_after_run():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "A1", "deps": []}])
    assert not rt.is_complete()
    rt.run()
    assert rt.is_complete()


def test_status_report():
    rt = WorkflowRuntime(max_workers=2)
    rt.load_workflow([{"id": "X1", "deps": []}, {"id": "X2", "deps": []}])
    status = rt.status()
    assert "total_tasks" in status
    assert "safety_violations" in status
    assert status["total_tasks"] == 2


def test_governance_report_shows_states():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "G1", "deps": []}])
    report = rt.governance_report()
    assert "total" in report
    assert report["total"] == 1
    assert "counts" in report


def test_safety_blocks_live_mode_task():
    rt = WorkflowRuntime()
    result = rt.load_workflow([{"id": "live_mode_runner", "deps": []}])
    assert result["valid"] is False
    assert any("live_mode" in v for v in result["violations"])


def test_execution_log_populated():
    rt = WorkflowRuntime(max_workers=3)
    rt.load_workflow([{"id": "L1", "deps": []}, {"id": "L2", "deps": []}])
    rt.run()
    assert len(rt.execution_log) >= 2
