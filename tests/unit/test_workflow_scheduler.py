"""Tests for Workflow Scheduler."""
from __future__ import annotations

from core.agent_factory import ExecutionMode, TaskStatus
from core.workflow_scheduler import WorkflowScheduler


def test_scheduler_creation():
    s = WorkflowScheduler(max_workers=3)
    assert s.worker_pool.max_workers == 3


def test_load_tasks():
    s = WorkflowScheduler(max_workers=2)
    s.load_tasks([{"id": "T1", "deps": []}, {"id": "T2", "deps": ["T1"]}])
    assert "T1" in s.factory.tasks
    assert "T2" in s.factory.tasks


def test_schedule_step_parallel():
    s = WorkflowScheduler(max_workers=3)
    s.load_tasks([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": []},
        {"id": "T3", "deps": []},
    ])
    step = s.schedule_step()
    assert len(step["assigned"]) == 3
    assert len(step["ready"]) == 3


def test_schedule_step_capacity_limit():
    s = WorkflowScheduler(max_workers=2)
    s.load_tasks([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": []},
        {"id": "T3", "deps": []},
    ])
    step = s.schedule_step()
    assert len(step["assigned"]) == 2
    assert len(step["blocked_by_capacity"]) == 1


def test_complete_task():
    s = WorkflowScheduler(max_workers=2)
    s.load_tasks([{"id": "T1", "deps": []}])
    s.schedule_step()
    result = s.complete_task("T1")
    assert result["status"] == "PASS"
    assert result["worker_released"] == "W1"


def test_dependency_ordering():
    s = WorkflowScheduler(max_workers=5)
    s.load_tasks([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": ["T1"]},
        {"id": "T3", "deps": ["T1", "T2"]},
    ])

    # T1 ready, T2/T3 blocked
    step1 = s.schedule_step()
    assert "T1" in step1["assigned"]
    assert "T2" not in step1["assigned"]

    # Complete T1
    s.complete_task("T1")

    # T2 now ready
    step2 = s.schedule_step()
    assert "T2" in step2["assigned"]
    assert "T3" not in step2["assigned"]

    # Complete T2
    s.complete_task("T2")

    # T3 now ready
    step3 = s.schedule_step()
    assert "T3" in step3["assigned"]


def test_run_to_completion():
    s = WorkflowScheduler(max_workers=5)
    s.load_tasks([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": ["T1"]},
        {"id": "T3", "deps": ["T2"]},
    ])
    steps = s.run_to_completion()
    assert s.is_complete()
    assert len(s.factory.completed) == 3


def test_summary():
    s = WorkflowScheduler(max_workers=5)
    s.load_tasks([{"id": "T1", "deps": []}, {"id": "T2", "deps": []}])
    s.run_to_completion()
    summary = s.summary()
    assert summary["total_tasks"] == 2
    assert summary["completed"] == 2
    assert summary["is_complete"]


def test_dag_mode():
    s = WorkflowScheduler(max_workers=5, mode=ExecutionMode.DAG)
    s.load_tasks([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": []},
        {"id": "T3", "deps": ["T1", "T2"]},
    ])
    steps = s.run_to_completion()
    assert s.is_complete()


def test_execution_log():
    s = WorkflowScheduler(max_workers=5)
    s.load_tasks([{"id": "T1", "deps": []}])
    s.run_to_completion()
    assert len(s.execution_log) == 1
    assert s.execution_log[0]["task"] == "T1"


def test_worker_recycling():
    s = WorkflowScheduler(max_workers=1)
    s.load_tasks([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": ["T1"]},
        {"id": "T3", "deps": ["T2"]},
    ])
    steps = s.run_to_completion()
    assert s.is_complete()
    assert s.worker_pool.status()["tasks_completed"] == 3
