"""Governance State Model — formal workflow lifecycle state machine.

Runtime-independent pure state logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class State(Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    CLOSED = "CLOSED"


# Valid transitions: (from_state, to_state)
VALID_TRANSITIONS = {
    State.NEW: {State.READY, State.BLOCKED},
    State.READY: {State.RUNNING, State.BLOCKED},
    State.RUNNING: {State.PASS, State.PARTIAL, State.FAIL, State.BLOCKED},
    State.PASS: {State.CLOSED},
    State.PARTIAL: {State.CLOSED, State.RUNNING},  # can retry
    State.FAIL: {State.CLOSED, State.RUNNING},  # can retry
    State.BLOCKED: {State.READY, State.RUNNING},
    State.CLOSED: set(),  # terminal
}

# Terminal states (no further transitions)
TERMINAL_STATES = {State.CLOSED}

# Success states (task completed successfully)
SUCCESS_STATES = {State.PASS, State.CLOSED}

# Failure states (task failed or partially failed)
FAILURE_STATES = {State.PARTIAL, State.FAIL}


@dataclass
class StateTransition:
    from_state: State
    to_state: State
    reason: str = ""

    def is_valid(self) -> bool:
        return self.to_state in VALID_TRANSITIONS.get(self.from_state, set())


@dataclass
class TaskState:
    task_id: str
    state: State = State.NEW
    deps: list[str] = field(default_factory=list)
    history: list[StateTransition] = field(default_factory=list)

    def can_transition(self, target: State) -> bool:
        if self.state in TERMINAL_STATES:
            return False
        return target in VALID_TRANSITIONS.get(self.state, set())

    def transition(self, target: State, reason: str = "") -> StateTransition:
        if not self.can_transition(target):
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {target.value} "
                f"(valid: {[s.value for s in VALID_TRANSITIONS.get(self.state, set())]})"
            )
        transition = StateTransition(from_state=self.state, to_state=target, reason=reason)
        self.state = target
        self.history.append(transition)
        return transition

    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def is_success(self) -> bool:
        return self.state in SUCCESS_STATES

    def is_failure(self) -> bool:
        return self.state in FAILURE_STATES

    def summary(self) -> dict:
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "deps": self.deps,
            "transitions": len(self.history),
            "is_terminal": self.is_terminal(),
        }


class GovernanceStateMachine:
    def __init__(self):
        self.tasks: dict[str, TaskState] = {}
        self.history: list[dict] = []

    def register(self, task_id: str, deps: list[str] | None = None) -> TaskState:
        task = TaskState(task_id=task_id, deps=deps or [])
        self.tasks[task_id] = task
        return task

    def resolve_ready(self) -> list[str]:
        """Find tasks that can be marked READY (all deps satisfied)."""
        ready = []
        completed = {
            tid for tid, t in self.tasks.items()
            if t.state in SUCCESS_STATES
        }
        for tid, task in self.tasks.items():
            if task.state == State.NEW:
                if all(dep in completed for dep in task.deps):
                    ready.append(tid)
        return ready

    def transition(self, task_id: str, target: State, reason: str = "") -> StateTransition:
        task = self.tasks[task_id]
        transition = task.transition(target, reason)
        self.history.append({
            "task": task_id,
            "from": transition.from_state.value,
            "to": transition.to_state.value,
            "reason": reason,
        })
        return transition

    def can_closeout(self) -> tuple[bool, list[str]]:
        """Check if all tasks can be closed out.

        A task is closeable if it is already terminal (CLOSED) or in a
        success state (PASS) that can transition to CLOSED.
        """
        unclosed = []
        for tid, task in self.tasks.items():
            if not task.is_terminal() and task.state != State.PASS:
                unclosed.append(tid)
        return len(unclosed) == 0, unclosed

    def closeout(self) -> dict:
        """Close all terminal tasks."""
        closed = []
        for tid, task in self.tasks.items():
            if task.state in SUCCESS_STATES and not task.is_terminal():
                task.transition(State.CLOSED, reason="closeout")
                closed.append(tid)
        return {"closed": closed, "remaining": [t for t in self.tasks if not self.tasks[t].is_terminal()]}

    def state_summary(self) -> dict:
        counts = {}
        for task in self.tasks.values():
            s = task.state.value
            counts[s] = counts.get(s, 0) + 1
        return {
            "total": len(self.tasks),
            "counts": counts,
            "ready": self.resolve_ready(),
            "can_closeout": self.can_closeout()[0],
        }

    def validate_all_transitions(self) -> list[dict]:
        """Validate all recorded transitions are legal."""
        violations = []
        for record in self.history:
            from_state = State(record["from"])
            to_state = State(record["to"])
            if to_state not in VALID_TRANSITIONS.get(from_state, set()):
                violations.append(record)
        return violations
