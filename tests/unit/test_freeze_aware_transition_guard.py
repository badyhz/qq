from __future__ import annotations

import pytest

from core.freeze_aware_transition_guard import (
    TRANSITIONS,
    FreezeAwareTransitionGuard,
    validate_transition,
)


class TestFreezeAwareTransitionGuard:
    def test_create_guard(self) -> None:
        g = FreezeAwareTransitionGuard(
            from_state="NOT_STARTED",
            to_state="IN_PROGRESS",
            guard_condition="admission_passed",
            requires_human_approval=False,
        )
        assert g.from_state == "NOT_STARTED"
        assert g.to_state == "IN_PROGRESS"

    def test_frozen(self) -> None:
        g = FreezeAwareTransitionGuard("A", "B", "c", False)
        with pytest.raises(AttributeError):
            g.from_state = "X"  # type: ignore[misc]

    def test_transitions_tuple(self) -> None:
        assert isinstance(TRANSITIONS, tuple)
        assert len(TRANSITIONS) > 0
        for t in TRANSITIONS:
            assert len(t) == 4

    def test_validate_transition_valid(self) -> None:
        assert validate_transition("NOT_STARTED", "IN_PROGRESS") is True
        assert validate_transition("IN_PROGRESS", "COMPLETED") is True
        assert validate_transition("COMPLETED", "PASS") is True

    def test_validate_transition_invalid(self) -> None:
        assert validate_transition("PASS", "NOT_STARTED") is False
        assert validate_transition("DENIED", "IN_PROGRESS") is False
        assert validate_transition("BOGUS", "X") is False

    def test_human_approval_transitions(self) -> None:
        human_transitions = [t for t in TRANSITIONS if t[3] is True]
        assert len(human_transitions) > 0
        for t in human_transitions:
            assert isinstance(t[3], bool)

    def test_pass_to_pass_no_op(self) -> None:
        assert validate_transition("PASS", "PASS") is True
