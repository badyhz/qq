"""Integration tests: multi-agent collision prevention via governance components.

Reproduces the T707 vs T710 scenario where two agents race on
core/worker_pool.py and validates that ownership, locking, and merge
review governance catch every collision path.
"""
from __future__ import annotations

import pytest

from core.component_ownership import ConflictError, ComponentOwnershipRegistry
from core.workflow_lock_manager import LockError, WorkflowLockManager
from core.merge_review import MergeReviewPipeline, ReviewStatus


COMP = "core/worker_pool.py"
T707 = "T707"
T710 = "T710"
HASH_A = "abc123"
HASH_B = "def456"


# ── 1. ownership prevents overwrite ────────────────────────────────────
def test_ownership_prevents_overwrite():
    reg = ComponentOwnershipRegistry()
    reg.register(COMP, T707, "worker_pool_builder")
    with pytest.raises(ConflictError):
        reg.register(COMP, T710, "e2e_builder")


# ── 2. lock prevents concurrent write ──────────────────────────────────
def test_lock_prevents_concurrent_write():
    lm = WorkflowLockManager()
    lm.acquire(COMP, T707, "worker_pool_builder")
    with pytest.raises(LockError):
        lm.acquire(COMP, T710, "e2e_builder")


# ── 3. lock release allows takeover ────────────────────────────────────
def test_lock_release_allows_takeover():
    lm = WorkflowLockManager()
    lm.acquire(COMP, T707, "worker_pool_builder")
    lm.release(COMP, T707)
    info = lm.acquire(COMP, T710, "e2e_builder")
    assert info.holder_task == T710
    assert info.holder_agent == "e2e_builder"


# ── 4. merge review detects conflict ───────────────────────────────────
def test_merge_review_detects_conflict():
    pipeline = MergeReviewPipeline()
    pipeline.set_canonical(COMP, HASH_A)
    mr = pipeline.propose(COMP, T710, HASH_B, "e2e_builder")
    assert mr.status == ReviewStatus.CONFLICT
    assert mr.canonical_hash == HASH_A
    assert mr.candidate_hash == HASH_B


# ── 5. merge review accept updates canonical ───────────────────────────
def test_merge_review_accept_updates_canonical():
    pipeline = MergeReviewPipeline()
    pipeline.set_canonical(COMP, HASH_A)
    mr = pipeline.propose(COMP, T710, HASH_B, "e2e_builder")
    pipeline.review(mr.id, "admin", "looks good")
    pipeline.accept(mr.id, "admin")
    updated = pipeline.get(mr.id)
    assert updated.status == ReviewStatus.ACCEPTED
    # canonical should now be HASH_B
    assert pipeline._canonical_hashes[COMP] == HASH_B


# ── 6. full governance flow ────────────────────────────────────────────
def test_full_governance_flow():
    # T707 registers ownership
    ownership = ComponentOwnershipRegistry()
    ownership.register(COMP, T707, "worker_pool_builder")

    # T710 blocked by ownership
    with pytest.raises(ConflictError):
        ownership.register(COMP, T710, "e2e_builder")

    # T707 acquires lock, writes, releases
    locks = WorkflowLockManager()
    locks.acquire(COMP, T707, "worker_pool_builder")
    with pytest.raises(LockError):
        locks.acquire(COMP, T710, "e2e_builder")
    locks.release(COMP, T707)

    # T710 proposes merge after T707's write
    pipeline = MergeReviewPipeline()
    pipeline.set_canonical(COMP, HASH_A)  # T707's written content
    mr = pipeline.propose(COMP, T710, HASH_B, "e2e_builder")
    assert mr.status == ReviewStatus.CONFLICT
    pipeline.review(mr.id, "admin", "merge approved")
    pipeline.accept(mr.id, "admin")
    assert pipeline.get(mr.id).status == ReviewStatus.ACCEPTED


# ── 7. concurrent agents blocked ───────────────────────────────────────
def test_concurrent_agents_blocked():
    locks = WorkflowLockManager()
    info_a = locks.try_acquire(COMP, T707, "worker_pool_builder")
    info_b = locks.try_acquire(COMP, T710, "e2e_builder")
    assert info_a is not None
    assert info_b is None  # blocked, no exception

    # Meanwhile try_acquire on a different component should succeed
    other = "core/signal_engine.py"
    info_c = locks.try_acquire(other, T710, "e2e_builder")
    assert info_c is not None


# ── 8. governance summary ──────────────────────────────────────────────
def test_governance_summary():
    ownership = ComponentOwnershipRegistry()
    ownership.register("core/worker_pool.py", T707, "worker_pool_builder")
    ownership.register("core/signal_engine.py", T710, "e2e_builder")

    locks = WorkflowLockManager()
    locks.acquire("core/worker_pool.py", T707, "worker_pool_builder")
    locks.acquire("core/signal_engine.py", T710, "e2e_builder")

    pipeline = MergeReviewPipeline()
    pipeline.set_canonical("core/worker_pool.py", HASH_A)
    mr = pipeline.propose("core/worker_pool.py", T710, HASH_B, "e2e_builder")
    pipeline.review(mr.id, "admin")

    # Ownership summary
    os = ownership.summary()
    assert os["total_components"] == 2
    assert os["tasks"][T707] == 1
    assert os["tasks"][T710] == 1

    # Lock summary
    ls = locks.summary()
    assert ls["total_locks"] == 2
    assert ls["unique_agents"] == 2
    assert "core/worker_pool.py" in ls["locked_components"]
    assert "core/signal_engine.py" in ls["locked_components"]

    # Merge review summary
    ps = pipeline.summary()
    assert ps["total_mrs"] == 1
    assert ps["open_mrs"] == 1
    assert ps["by_status"]["reviewing"] == 1
    assert ps["tracked_components"] == 1
