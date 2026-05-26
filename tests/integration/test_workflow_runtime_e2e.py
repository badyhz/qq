"""End-to-End Workflow Simulation — integration tests.

Simulates Execution Guard Phase2 pipeline using all runtime components.
No real agents. No filesystem mutation.
"""
from __future__ import annotations

import pytest

from core.agent_factory import AgentFactory, ExecutionMode, Task, TaskStatus
from core.governance_state import GovernanceStateMachine, State
from core.worker_pool import WorkerPool
from core.workflow_runner import WorkflowRunner
from core.workflow_scheduler import WorkflowScheduler
from core.workflow_safety import (
    Severity,
    WorkflowSafetyValidator,
    validate_workflow_safety,
)


# --- QUEUE_MODE E2E ---


def test_queue_mode_guard_injection():
    """Simulate guard injection pipeline in QUEUE mode."""
    runner = WorkflowRunner("GUARD_INJECTION_BATCH")
    runner.build_from_template()

    # Verify queue structure
    plan = runner.plan()
    assert plan["mode"] == "QUEUE_MODE"
    assert plan["total_tasks"] == 5

    # Execute
    results = runner.simulate_execution()
    assert len(results) == 5
    assert all(r["status"] == "PASS" for r in results)


def test_queue_mode_sequential_ordering():
    """Verify QUEUE mode plans sequential execution via AgentFactory."""
    scheduler = WorkflowScheduler(max_workers=5, mode=ExecutionMode.QUEUE)
    scheduler.load_tasks([
        {"id": "T1", "deps": []},
        {"id": "T2", "deps": []},
        {"id": "T3", "deps": []},
    ])

    # QUEUE mode: AgentFactory plan has 3 waves of 1 task each
    plan = scheduler.factory.plan()
    assert len(plan.waves) == 3
    assert all(len(w) == 1 for w in plan.waves)

    # Full execution still completes
    steps = scheduler.run_to_completion()
    assert scheduler.is_complete()


# --- DAG_MODE E2E ---


def test_dag_mode_parallel_execution():
    """Simulate parallel batch execution in DAG mode."""
    scheduler = WorkflowScheduler(max_workers=5, mode=ExecutionMode.DAG)
    scheduler.load_tasks([
        {"id": "T676", "deps": []},
        {"id": "T677", "deps": []},
        {"id": "T678", "deps": []},
        {"id": "T679", "deps": []},
        {"id": "T680", "deps": []},
        {"id": "T681", "deps": ["T676"]},
        {"id": "T682", "deps": ["T679"]},
    ])

    # Wave 1: 5 independent tasks
    step1 = scheduler.schedule_step()
    assert len(step1["assigned"]) == 5

    # Complete all wave 1
    for tid in step1["assigned"]:
        scheduler.complete_task(tid)

    # Wave 2: 2 dependent tasks
    step2 = scheduler.schedule_step()
    assert len(step2["assigned"]) == 2

    # Complete wave 2
    for tid in step2["assigned"]:
        scheduler.complete_task(tid)

    assert scheduler.is_complete()


def test_dag_mode_dependency_propagation():
    """Verify DAG mode respects dependencies."""
    scheduler = WorkflowScheduler(max_workers=10, mode=ExecutionMode.DAG)
    scheduler.load_tasks([
        {"id": "A", "deps": []},
        {"id": "B", "deps": ["A"]},
        {"id": "C", "deps": ["A"]},
        {"id": "D", "deps": ["B", "C"]},
    ])

    # Only A ready
    step1 = scheduler.schedule_step()
    assert step1["assigned"] == ["A"]

    scheduler.complete_task("A")

    # B and C now ready
    step2 = scheduler.schedule_step()
    assert set(step2["assigned"]) == {"B", "C"}

    scheduler.complete_task("B")
    scheduler.complete_task("C")

    # D now ready
    step3 = scheduler.schedule_step()
    assert step3["assigned"] == ["D"]


# --- CLOSEOUT_MODE E2E ---


def test_closeout_mode_sequential_verification():
    """Simulate closeout pipeline."""
    runner = WorkflowRunner("ENGINEERING_CLOSEOUT")
    runner.build_from_template()

    plan = runner.plan()
    assert plan["mode"] == "CLOSEOUT_MODE"
    assert plan["total_tasks"] == 7

    results = runner.simulate_execution()
    assert len(results) == 7

    # Verify closeout steps in order
    expected_order = [
        "verify_clean_tree", "classify_dirty", "check_frozen",
        "stage", "commit", "tag", "verify",
    ]
    actual_order = [r["task"] for r in results]
    assert actual_order == expected_order


def test_closeout_mode_worker_recycling():
    """Verify closeout reuses single worker."""
    scheduler = WorkflowScheduler(max_workers=1, mode=ExecutionMode.CLOSEOUT)
    scheduler.load_tasks([
        {"id": "verify_tree", "deps": []},
        {"id": "stage", "deps": ["verify_tree"]},
        {"id": "commit", "deps": ["stage"]},
        {"id": "tag", "deps": ["commit"]},
    ])

    steps = scheduler.run_to_completion()
    assert scheduler.is_complete()
    assert scheduler.worker_pool.status()["tasks_completed"] == 4


# --- SAFETY LAYER E2E ---


def test_safety_blocks_forbidden_tasks():
    """Verify safety layer blocks forbidden task patterns."""
    workflow = {
        "mode": "DAG",
        "tasks": [
            {"id": "runtime_integration_task", "deps": []},
            {"id": "planner_integration_task", "deps": []},
        ],
    }
    result = validate_workflow_safety(workflow)
    assert not result["safe"]
    assert len(result["violations"]) >= 2


def test_safety_allows_clean_workflow():
    """Verify safety layer allows clean workflow."""
    workflow = {
        "mode": "DAG",
        "tasks": [
            {"id": "inject_scripts", "deps": []},
            {"id": "create_tests", "deps": ["inject_scripts"]},
        ],
    }
    result = validate_workflow_safety(workflow)
    assert result["safe"]


def test_safety_blocks_frozen_access():
    """Verify safety layer blocks frozen file access."""
    validator = WorkflowSafetyValidator()
    violations = validator.validate_frozen_exclusion("T1", ["live_runner.py"])
    assert len(violations) > 0
    assert violations[0].severity == Severity.CRITICAL


# --- WORKER POOL E2E ---


def test_worker_pool_parallel_capacity():
    """Verify worker pool handles parallel capacity."""
    pool = WorkerPool(max_workers=3)

    # Assign 3 tasks
    pool.assign("T1")
    pool.assign("T2")
    pool.assign("T3")

    assert pool.available_slots() == 0
    assert not pool.can_assign()

    # Complete one, verify slot opens
    pool.complete("T1")
    assert pool.available_slots() == 1
    assert pool.can_assign()


def test_worker_pool_status_tracking():
    """Verify worker pool tracks status correctly."""
    pool = WorkerPool(max_workers=2)
    pool.assign("T1")

    status = pool.status()
    assert status["busy"] == 1
    assert status["idle"] == 1
    assert status["tasks_assigned"] == 1

    pool.complete("T1")
    status = pool.status()
    assert status["busy"] == 0
    assert status["idle"] == 2
    assert status["tasks_completed"] == 1


# --- GOVERNANCE STATE E2E ---


def test_governance_state_lifecycle():
    """Verify full governance state lifecycle."""
    sm = GovernanceStateMachine()
    sm.register("T1", deps=[])
    sm.register("T2", deps=["T1"])
    sm.register("T3", deps=["T1", "T2"])

    # T1 ready
    ready = sm.resolve_ready()
    assert ready == ["T1"]

    # Execute T1
    sm.transition("T1", State.READY)
    sm.transition("T1", State.RUNNING)
    sm.transition("T1", State.PASS)

    # T2 ready
    ready = sm.resolve_ready()
    assert ready == ["T2"]

    # Execute T2
    sm.transition("T2", State.READY)
    sm.transition("T2", State.RUNNING)
    sm.transition("T2", State.PASS)

    # T3 ready
    ready = sm.resolve_ready()
    assert ready == ["T3"]

    # Execute T3
    sm.transition("T3", State.READY)
    sm.transition("T3", State.RUNNING)
    sm.transition("T3", State.PASS)

    # All done
    can, remaining = sm.can_closeout()
    assert can
    assert remaining == []


# --- FULL PIPELINE E2E ---


def test_full_phase2_simulation():
    """Simulate full Phase2 pipeline: audit -> inject -> test -> sync -> closeout."""
    # Step 1: Audit (DAG)
    audit_scheduler = WorkflowScheduler(max_workers=5, mode=ExecutionMode.DAG)
    audit_scheduler.load_tasks([
        {"id": "scan", "deps": []},
        {"id": "check_frozen", "deps": ["scan"]},
        {"id": "classify", "deps": ["scan"]},
    ])
    audit_scheduler.run_to_completion()
    assert audit_scheduler.is_complete()

    # Step 2: Inject (QUEUE)
    inject_scheduler = WorkflowScheduler(max_workers=1, mode=ExecutionMode.QUEUE)
    inject_scheduler.load_tasks([
        {"id": "inject", "deps": []},
        {"id": "test", "deps": ["inject"]},
    ])
    inject_scheduler.run_to_completion()
    assert inject_scheduler.is_complete()

    # Step 3: Docs sync (DAG)
    sync_scheduler = WorkflowScheduler(max_workers=5, mode=ExecutionMode.DAG)
    sync_scheduler.load_tasks([
        {"id": "sync_matrix", "deps": []},
        {"id": "sync_dashboard", "deps": []},
        {"id": "sync_metrics", "deps": []},
    ])
    sync_scheduler.run_to_completion()
    assert sync_scheduler.is_complete()

    # Step 4: Closeout
    closeout_runner = WorkflowRunner("ENGINEERING_CLOSEOUT")
    closeout_runner.build_from_template()
    results = closeout_runner.simulate_execution()
    assert len(results) == 7
