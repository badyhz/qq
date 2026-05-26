"""Tests for Component Ownership Registry."""
from __future__ import annotations

import pytest

from core.component_ownership import ComponentOwnershipRegistry, ConflictError


def test_register_new_component():
    reg = ComponentOwnershipRegistry()
    entry = reg.register("core/worker_pool.py", "T707", "builder")
    assert entry.owner_task == "T707"
    assert entry.owner_agent == "builder"
    assert entry.component_path == "core/worker_pool.py"
    assert entry.permission == "exclusive"


def test_register_duplicate_raises_conflict():
    reg = ComponentOwnershipRegistry()
    reg.register("core/worker_pool.py", "T707")
    with pytest.raises(ConflictError, match="owned by task 'T707'"):
        reg.register("core/worker_pool.py", "T710")


def test_check_owner_can_write():
    reg = ComponentOwnershipRegistry()
    reg.register("core/worker_pool.py", "T707")
    assert reg.check("core/worker_pool.py", "T707") is True


def test_check_non_owner_cannot_write():
    reg = ComponentOwnershipRegistry()
    reg.register("core/worker_pool.py", "T707")
    assert reg.check("core/worker_pool.py", "T710") is False


def test_check_unowned_component():
    reg = ComponentOwnershipRegistry()
    assert reg.check("core/nonexistent.py", "T707") is True


def test_release_allows_reassign():
    reg = ComponentOwnershipRegistry()
    reg.register("core/worker_pool.py", "T707")
    reg.release("core/worker_pool.py", "T707")
    # After release, T710 can register
    entry = reg.register("core/worker_pool.py", "T710")
    assert entry.owner_task == "T710"


def test_release_non_owner_raises():
    reg = ComponentOwnershipRegistry()
    reg.register("core/worker_pool.py", "T707")
    with pytest.raises(ConflictError, match="does not own"):
        reg.release("core/worker_pool.py", "T710")


def test_list_owned_components():
    reg = ComponentOwnershipRegistry()
    reg.register("core/worker_pool.py", "T707")
    reg.register("core/workflow_scheduler.py", "T707")
    reg.register("core/governance_state.py", "T708")
    owned = reg.list_owned("T707")
    assert set(owned) == {"core/worker_pool.py", "core/workflow_scheduler.py"}


def test_summary_stats():
    reg = ComponentOwnershipRegistry()
    reg.register("core/worker_pool.py", "T707")
    reg.register("core/workflow_scheduler.py", "T707")
    reg.register("core/governance_state.py", "T708")
    reg.register("core/agent_factory.py", "T709", permission="shared")
    s = reg.summary()
    assert s["total_components"] == 4
    assert s["tasks"]["T707"] == 2
    assert s["tasks"]["T708"] == 1
    assert s["permissions"]["exclusive"] == 3
    assert s["permissions"]["shared"] == 1


def test_exclusive_vs_shared_permission():
    reg = ComponentOwnershipRegistry()
    reg.register("core/agent_factory.py", "T707", permission="shared")
    # T708 can write because permission is shared
    assert reg.check("core/agent_factory.py", "T708") is True
    reg.register("core/worker_pool.py", "T710", permission="exclusive")
    # T707 cannot write because permission is exclusive
    assert reg.check("core/worker_pool.py", "T707") is False


def test_conflict_detection():
    reg = ComponentOwnershipRegistry()
    assert reg.conflicts() == []


def test_get_owner():
    reg = ComponentOwnershipRegistry()
    entry = reg.register("core/worker_pool.py", "T707", "builder")
    result = reg.get_owner("core/worker_pool.py")
    assert result is entry
    assert reg.get_owner("core/nonexistent.py") is None


def test_release_unregistered_raises():
    reg = ComponentOwnershipRegistry()
    with pytest.raises(ConflictError, match="No ownership entry"):
        reg.release("core/nonexistent.py", "T707")
