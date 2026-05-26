"""Tests for Simulated Worker Pool."""
from __future__ import annotations

from core.worker_pool import WorkerPool, WorkerState


def test_pool_creation():
    pool = WorkerPool(max_workers=3)
    assert pool.max_workers == 3
    assert len(pool.workers) == 3


def test_all_idle_initially():
    pool = WorkerPool(max_workers=5)
    assert pool.available_slots() == 5
    assert len(pool.idle_workers()) == 5


def test_assign_task():
    pool = WorkerPool(max_workers=2)
    assignment = pool.assign("T1")
    assert assignment is not None
    assert assignment.worker_id == "W1"
    assert assignment.task_id == "T1"
    assert pool.available_slots() == 1


def test_assign_exhausts_pool():
    pool = WorkerPool(max_workers=2)
    pool.assign("T1")
    pool.assign("T2")
    assignment = pool.assign("T3")
    assert assignment is None
    assert pool.available_slots() == 0


def test_complete_task():
    pool = WorkerPool(max_workers=2)
    pool.assign("T1")
    worker = pool.complete("T1")
    assert worker is not None
    assert worker.is_idle()
    assert pool.available_slots() == 2
    assert "T1" in pool.completed


def test_complete_nonexistent():
    pool = WorkerPool(max_workers=2)
    worker = pool.complete("NONEXISTENT")
    assert worker is None


def test_status():
    pool = WorkerPool(max_workers=3)
    pool.assign("T1")
    pool.assign("T2")
    status = pool.status()
    assert status["total_workers"] == 3
    assert status["busy"] == 2
    assert status["idle"] == 1
    assert status["tasks_assigned"] == 2


def test_can_assign():
    pool = WorkerPool(max_workers=1)
    assert pool.can_assign()
    pool.assign("T1")
    assert not pool.can_assign()
    pool.complete("T1")
    assert pool.can_assign()


def test_multiple_completions():
    pool = WorkerPool(max_workers=3)
    pool.assign("T1")
    pool.assign("T2")
    pool.assign("T3")
    pool.complete("T1")
    pool.complete("T2")
    pool.complete("T3")
    assert len(pool.completed) == 3
    assert pool.available_slots() == 3


def test_worker_states():
    pool = WorkerPool(max_workers=2)
    pool.assign("T1")
    status = pool.status()
    assert status["workers"]["W1"]["state"] == "BUSY"
    assert status["workers"]["W1"]["task"] == "T1"
    assert status["workers"]["W2"]["state"] == "IDLE"


def test_assign_after_complete():
    pool = WorkerPool(max_workers=1)
    pool.assign("T1")
    pool.complete("T1")
    assignment = pool.assign("T2")
    assert assignment is not None
    assert assignment.worker_id == "W1"
