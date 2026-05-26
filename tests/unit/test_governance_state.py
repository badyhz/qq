"""Tests for Governance State Model."""
from __future__ import annotations

import pytest

from core.governance_state import (
    GovernanceStateMachine,
    State,
    StateTransition,
    TaskState,
    VALID_TRANSITIONS,
)


def test_task_creation():
    t = TaskState(task_id="T1")
    assert t.state == State.NEW
    assert not t.is_terminal()


def test_valid_transition():
    t = TaskState(task_id="T1")
    assert t.can_transition(State.READY)
    t.transition(State.READY)
    assert t.state == State.READY


def test_invalid_transition():
    t = TaskState(task_id="T1")
    assert not t.can_transition(State.PASS)  # NEW -> PASS not valid
    with pytest.raises(ValueError, match="Invalid transition"):
        t.transition(State.PASS)


def test_terminal_states():
    for terminal in [State.CLOSED]:
        t = TaskState(task_id="T1")
        t.state = terminal
        assert t.is_terminal()
        assert not t.can_transition(State.READY)


def test_success_states():
    t = TaskState(task_id="T1")
    t.state = State.PASS
    assert t.is_success()
    assert not t.is_failure()


def test_failure_states():
    for fail_state in [State.PARTIAL, State.FAIL]:
        t = TaskState(task_id="T1")
        t.state = fail_state
        assert t.is_failure()


def test_dependency_resolution():
    sm = GovernanceStateMachine()
    sm.register("T1", deps=[])
    sm.register("T2", deps=["T1"])
    sm.register("T3", deps=["T1", "T2"])

    # Initially only T1 is ready (no deps)
    ready = sm.resolve_ready()
    assert ready == ["T1"]

    # Complete T1
    sm.transition("T1", State.READY)
    sm.transition("T1", State.RUNNING)
    sm.transition("T1", State.PASS)

    # Now T2 is ready
    ready = sm.resolve_ready()
    assert ready == ["T2"]

    # Complete T2
    sm.transition("T2", State.READY)
    sm.transition("T2", State.RUNNING)
    sm.transition("T2", State.PASS)

    # Now T3 is ready
    ready = sm.resolve_ready()
    assert ready == ["T3"]


def test_blocked_detection():
    sm = GovernanceStateMachine()
    sm.register("T1", deps=["T0"])  # T0 doesn't exist
    ready = sm.resolve_ready()
    assert ready == []  # T1 blocked because dep not satisfied


def test_closeout():
    sm = GovernanceStateMachine()
    sm.register("T1")
    sm.register("T2")

    sm.transition("T1", State.READY)
    sm.transition("T1", State.RUNNING)
    sm.transition("T1", State.PASS)

    sm.transition("T2", State.READY)
    sm.transition("T2", State.RUNNING)
    sm.transition("T2", State.PASS)

    can, remaining = sm.can_closeout()
    assert can
    assert remaining == []

    result = sm.closeout()
    assert len(result["closed"]) == 2


def test_closeout_with_pending():
    sm = GovernanceStateMachine()
    sm.register("T1")
    sm.register("T2")

    sm.transition("T1", State.READY)
    sm.transition("T1", State.RUNNING)
    sm.transition("T1", State.PASS)

    # T2 still NEW
    can, remaining = sm.can_closeout()
    assert not can
    assert remaining == ["T2"]


def test_retry_from_partial():
    sm = GovernanceStateMachine()
    sm.register("T1")
    sm.transition("T1", State.READY)
    sm.transition("T1", State.RUNNING)
    sm.transition("T1", State.PARTIAL)

    # Can retry from PARTIAL
    assert sm.tasks["T1"].can_transition(State.RUNNING)
    sm.transition("T1", State.RUNNING, reason="retry")
    assert sm.tasks["T1"].state == State.RUNNING


def test_state_summary():
    sm = GovernanceStateMachine()
    sm.register("T1")
    sm.register("T2")
    sm.transition("T1", State.READY)

    summary = sm.state_summary()
    assert summary["total"] == 2
    assert summary["counts"]["READY"] == 1
    assert summary["counts"]["NEW"] == 1


def test_history_tracking():
    sm = GovernanceStateMachine()
    sm.register("T1")
    sm.transition("T1", State.READY, reason="deps met")
    sm.transition("T1", State.RUNNING, reason="started")

    assert len(sm.history) == 2
    assert sm.history[0]["reason"] == "deps met"


def test_validate_transitions():
    sm = GovernanceStateMachine()
    sm.register("T1")
    sm.transition("T1", State.READY)
    sm.transition("T1", State.RUNNING)
    sm.transition("T1", State.PASS)

    violations = sm.validate_all_transitions()
    assert len(violations) == 0


def test_all_valid_transitions_exist():
    """Verify all expected transitions are defined."""
    expected = {
        State.NEW: {State.READY, State.BLOCKED},
        State.READY: {State.RUNNING, State.BLOCKED},
        State.RUNNING: {State.PASS, State.PARTIAL, State.FAIL, State.BLOCKED},
        State.PASS: {State.CLOSED},
        State.PARTIAL: {State.CLOSED, State.RUNNING},
        State.FAIL: {State.CLOSED, State.RUNNING},
        State.BLOCKED: {State.READY, State.RUNNING},
        State.CLOSED: set(),
    }
    for state, targets in expected.items():
        assert state in VALID_TRANSITIONS, f"Missing transitions for {state}"
        assert VALID_TRANSITIONS[state] == targets, f"Wrong transitions for {state}"


def test_task_summary():
    t = TaskState(task_id="T1", deps=["T0"])
    summary = t.summary()
    assert summary["task_id"] == "T1"
    assert summary["state"] == "NEW"
    assert summary["deps"] == ["T0"]
