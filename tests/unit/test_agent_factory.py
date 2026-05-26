"""Tests for Agent Factory Harness."""
from __future__ import annotations

from core.agent_factory import AgentFactory, ExecutionMode, Task, TaskStatus


def test_task_creation():
    t = Task(id="T1", deps=[])
    assert t.status == TaskStatus.NEW
    assert t.is_ready(set())


def test_task_ready_with_deps():
    t = Task(id="T2", deps=["T1"])
    assert not t.is_ready(set())
    assert t.is_ready({"T1"})


def test_task_terminal():
    t = Task(id="T1")
    assert not t.is_terminal()
    t.status = TaskStatus.PASS
    assert t.is_terminal()


def test_register_task():
    f = AgentFactory()
    f.register(Task(id="T1"))
    assert "T1" in f.tasks


def test_dag_plan_parallel():
    f = AgentFactory(mode=ExecutionMode.DAG)
    f.register(Task(id="T1", deps=[]))
    f.register(Task(id="T2", deps=[]))
    f.register(Task(id="T3", deps=["T1", "T2"]))
    plan = f.plan()
    assert len(plan.waves) == 2
    assert set(plan.waves[0]) == {"T1", "T2"}
    assert plan.waves[1] == ["T3"]


def test_queue_plan_sequential():
    f = AgentFactory(mode=ExecutionMode.QUEUE)
    f.register(Task(id="T1", deps=[]))
    f.register(Task(id="T2", deps=[]))
    plan = f.plan()
    assert len(plan.waves) == 2
    assert len(plan.waves[0]) == 1
    assert len(plan.waves[1]) == 1


def test_closeout_plan():
    f = AgentFactory(mode=ExecutionMode.CLOSEOUT)
    plan = f.plan()
    assert len(plan.waves) == 7  # 7 closeout steps


def test_execute_task():
    f = AgentFactory()
    f.register(Task(id="T1"))
    f.execute_task("T1", TaskStatus.PASS)
    assert f.tasks["T1"].status == TaskStatus.PASS
    assert "T1" in f.completed


def test_blocker_detection():
    f = AgentFactory()
    f.register(Task(id="T1", deps=[]))
    f.register(Task(id="T2", deps=["T1"]))
    blockers = f.detect_blockers()
    assert "T2" in blockers
    assert blockers["T2"] == ["T1"]


def test_blocker_cleared():
    f = AgentFactory()
    f.register(Task(id="T1", deps=[]))
    f.register(Task(id="T2", deps=["T1"]))
    f.execute_task("T1", TaskStatus.PASS)
    blockers = f.detect_blockers()
    assert "T2" not in blockers


def test_state_summary():
    f = AgentFactory()
    f.register(Task(id="T1"))
    f.register(Task(id="T2"))
    f.execute_task("T1", TaskStatus.PASS)
    summary = f.state_summary()
    assert summary["total"] == 2
    assert summary["completed"] == 1
    assert summary["status_counts"]["PASS"] == 1


def test_multi_wave_dag():
    f = AgentFactory(mode=ExecutionMode.DAG)
    f.register(Task(id="T1"))
    f.register(Task(id="T2", deps=["T1"]))
    f.register(Task(id="T3", deps=["T1"]))
    f.register(Task(id="T4", deps=["T2", "T3"]))
    plan = f.plan()
    assert len(plan.waves) == 3
    assert plan.waves[0] == ["T1"]
    assert set(plan.waves[1]) == {"T2", "T3"}
    assert plan.waves[2] == ["T4"]


def test_partial_failure():
    f = AgentFactory()
    f.register(Task(id="T1"))
    f.register(Task(id="T2", deps=["T1"]))
    f.execute_task("T1", TaskStatus.PARTIAL)
    summary = f.state_summary()
    assert summary["status_counts"]["PARTIAL"] == 1
    assert "T1" not in f.completed  # PARTIAL doesn't clear deps


def test_execute_with_result():
    f = AgentFactory()
    f.register(Task(id="T1"))
    f.execute_task("T1", TaskStatus.PASS, result="41/41 guarded")
    assert f.tasks["T1"].result == "41/41 guarded"
    assert f.history[0]["result"] == "41/41 guarded"
