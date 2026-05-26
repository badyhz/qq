"""Tests for WorkflowLockManager."""

import pytest

from core.workflow_lock_manager import LockError, LockInfo, WorkflowLockManager


# ---------------------------------------------------------------------------
# 1. acquire_unlocked
# ---------------------------------------------------------------------------
def test_acquire_unlocked():
    mgr = WorkflowLockManager()
    info = mgr.acquire("core/worker_pool.py", "T707")
    assert info.holder_task == "T707"
    assert info.component_path == "core/worker_pool.py"
    assert isinstance(info.acquired_at, str)
    assert mgr.is_locked("core/worker_pool.py")


# ---------------------------------------------------------------------------
# 2. acquire_locked_raises
# ---------------------------------------------------------------------------
def test_acquire_locked_raises():
    mgr = WorkflowLockManager()
    mgr.acquire("core/worker_pool.py", "T707")
    with pytest.raises(LockError, match="locked by task"):
        mgr.acquire("core/worker_pool.py", "T999")


# ---------------------------------------------------------------------------
# 3. release_by_holder
# ---------------------------------------------------------------------------
def test_release_by_holder():
    mgr = WorkflowLockManager()
    mgr.acquire("core/worker_pool.py", "T707")
    mgr.release("core/worker_pool.py", "T707")
    assert not mgr.is_locked("core/worker_pool.py")
    assert mgr.get_holder("core/worker_pool.py") is None


# ---------------------------------------------------------------------------
# 4. release_by_non_holder_raises
# ---------------------------------------------------------------------------
def test_release_by_non_holder_raises():
    mgr = WorkflowLockManager()
    mgr.acquire("core/worker_pool.py", "T707")
    with pytest.raises(LockError, match="not the lock holder"):
        mgr.release("core/worker_pool.py", "T999")
    # Lock is still held
    assert mgr.is_locked("core/worker_pool.py")


# ---------------------------------------------------------------------------
# 5. try_acquire_returns_none_when_locked
# ---------------------------------------------------------------------------
def test_try_acquire_returns_none_when_locked():
    mgr = WorkflowLockManager()
    mgr.acquire("core/worker_pool.py", "T707")
    result = mgr.try_acquire("core/worker_pool.py", "T999")
    assert result is None


def test_try_acquire_succeeds_when_free():
    mgr = WorkflowLockManager()
    info = mgr.try_acquire("core/worker_pool.py", "T707")
    assert info is not None
    assert info.holder_task == "T707"


# ---------------------------------------------------------------------------
# 6. force_release_works
# ---------------------------------------------------------------------------
def test_force_release_works():
    mgr = WorkflowLockManager()
    mgr.acquire("core/worker_pool.py", "T707")
    released = mgr.force_release("core/worker_pool.py")
    assert released is not None
    assert released.holder_task == "T707"
    assert not mgr.is_locked("core/worker_pool.py")


def test_force_release_returns_none_when_not_locked():
    mgr = WorkflowLockManager()
    result = mgr.force_release("core/worker_pool.py")
    assert result is None


# ---------------------------------------------------------------------------
# 7. list_locks
# ---------------------------------------------------------------------------
def test_list_locks():
    mgr = WorkflowLockManager()
    mgr.acquire("a.py", "T1")
    mgr.acquire("b.py", "T2")
    locks = mgr.list_locks()
    assert len(locks) == 2
    paths = {l.component_path for l in locks}
    assert paths == {"a.py", "b.py"}


def test_list_locks_empty():
    mgr = WorkflowLockManager()
    assert mgr.list_locks() == []


# ---------------------------------------------------------------------------
# 8. summary_stats
# ---------------------------------------------------------------------------
def test_summary_stats():
    mgr = WorkflowLockManager()
    mgr.acquire("a.py", "T1", agent_id="agent-alpha")
    mgr.acquire("b.py", "T2", agent_id="agent-beta")
    s = mgr.summary()
    assert s["total_locks"] == 2
    assert s["unique_agents"] == 2
    assert sorted(s["locked_components"]) == ["a.py", "b.py"]


def test_summary_empty():
    mgr = WorkflowLockManager()
    s = mgr.summary()
    assert s["total_locks"] == 0
    assert s["unique_agents"] == 0
    assert s["locked_components"] == []


# ---------------------------------------------------------------------------
# 9. reentrant_same_task
# ---------------------------------------------------------------------------
def test_reentrant_same_task():
    mgr = WorkflowLockManager()
    info1 = mgr.acquire("core/worker_pool.py", "T707")
    info2 = mgr.acquire("core/worker_pool.py", "T707")
    # Both belong to same task
    assert info1.holder_task == info2.holder_task == "T707"
    # Timestamp should be updated on re-acquire
    assert info2.acquired_at >= info1.acquired_at


# ---------------------------------------------------------------------------
# 10. lock_after_release
# ---------------------------------------------------------------------------
def test_lock_after_release():
    mgr = WorkflowLockManager()
    mgr.acquire("core/worker_pool.py", "T707")
    mgr.release("core/worker_pool.py", "T707")
    info = mgr.acquire("core/worker_pool.py", "T999")
    assert info.holder_task == "T999"
    assert mgr.is_locked("core/worker_pool.py")
