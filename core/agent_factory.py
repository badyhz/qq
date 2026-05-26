"""Agent Factory Harness — minimal orchestration runtime.

Simulation only. No real agent execution.

Supports:
- QUEUE_MODE: sequential batch execution
- DAG_MODE: parallel independent tasks
- CLOSEOUT_MODE: phase closure verification
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    CLOSED = "CLOSED"


class ExecutionMode(Enum):
    QUEUE = "QUEUE_MODE"
    DAG = "DAG_MODE"
    CLOSEOUT = "CLOSEOUT_MODE"


@dataclass
class Task:
    id: str
    deps: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.NEW
    mode: ExecutionMode = ExecutionMode.DAG
    result: str | None = None

    def is_ready(self, completed: set[str]) -> bool:
        if self.status not in (TaskStatus.NEW, TaskStatus.BLOCKED):
            return False
        return all(dep in completed for dep in self.deps)

    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.PASS, TaskStatus.PARTIAL, TaskStatus.FAIL, TaskStatus.CLOSED)


@dataclass
class ExecutionPlan:
    mode: ExecutionMode
    waves: list[list[str]]  # list of waves, each wave is list of task ids
    blocked: list[str]
    ready: list[str]

    def summary(self) -> dict:
        return {
            "mode": self.mode.value,
            "waves": len(self.waves),
            "total_tasks": sum(len(w) for w in self.waves),
            "blocked": len(self.blocked),
            "ready": len(self.ready),
        }


class AgentFactory:
    def __init__(self, mode: ExecutionMode = ExecutionMode.DAG):
        self.mode = mode
        self.tasks: dict[str, Task] = {}
        self.completed: set[str] = set()
        self.history: list[dict] = []

    def register(self, task: Task) -> None:
        task.mode = self.mode
        self.tasks[task.id] = task

    def get_ready(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.is_ready(self.completed)]

    def get_blocked(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.status in (TaskStatus.NEW, TaskStatus.BLOCKED) and not t.is_ready(self.completed)]

    def get_all_terminal(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.is_terminal()]

    def plan(self) -> ExecutionPlan:
        """Compute execution waves based on mode and dependencies."""
        if self.mode == ExecutionMode.QUEUE:
            return self._plan_queue()
        elif self.mode == ExecutionMode.DAG:
            return self._plan_dag()
        elif self.mode == ExecutionMode.CLOSEOUT:
            return self._plan_closeout()
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _plan_queue(self) -> ExecutionPlan:
        """Queue mode: one task per wave, respecting dependencies."""
        waves = []
        remaining = {t.id for t in self.tasks.values() if not t.is_terminal()}
        simulated_completed = set(self.completed)

        while remaining:
            ready = [self.tasks[tid] for tid in remaining if self.tasks[tid].is_ready(simulated_completed)]
            if not ready:
                break
            # Queue: take first ready task only
            wave = [ready[0].id]
            waves.append(wave)
            remaining -= set(wave)
            simulated_completed.update(wave)

        blocked = [t.id for t in self.get_blocked()]
        ready = [t.id for t in self.get_ready()]

        return ExecutionPlan(mode=self.mode, waves=waves, blocked=blocked, ready=ready)

    def _plan_dag(self) -> ExecutionPlan:
        """DAG mode: maximize parallelism per wave."""
        waves = []
        remaining = {t.id for t in self.tasks.values() if not t.is_terminal()}
        simulated_completed = set(self.completed)

        while remaining:
            ready = [self.tasks[tid] for tid in remaining if self.tasks[tid].is_ready(simulated_completed)]
            if not ready:
                break
            wave = [t.id for t in ready]
            waves.append(wave)
            remaining -= set(wave)
            simulated_completed.update(wave)

        blocked = [t.id for t in self.get_blocked()]
        ready = [t.id for t in self.get_ready()]

        return ExecutionPlan(mode=self.mode, waves=waves, blocked=blocked, ready=ready)

    def _plan_closeout(self) -> ExecutionPlan:
        """Closeout mode: sequential verification steps."""
        closeout_steps = ["verify_clean_tree", "classify_dirty", "check_frozen", "stage", "commit", "tag", "verify"]
        waves = [[step] for step in closeout_steps]

        blocked = [t.id for t in self.get_blocked()]
        ready = [t.id for t in self.get_ready()]

        return ExecutionPlan(mode=self.mode, waves=waves, blocked=blocked, ready=ready)

    def execute_task(self, task_id: str, status: TaskStatus, result: str | None = None) -> None:
        """Simulate task execution."""
        task = self.tasks[task_id]
        task.status = status
        task.result = result

        if status == TaskStatus.PASS:
            self.completed.add(task_id)

        self.history.append({
            "task": task_id,
            "status": status.value,
            "result": result,
        })

    def detect_blockers(self) -> dict[str, list[str]]:
        """Detect what blocks each task."""
        blockers = {}
        for task in self.tasks.values():
            if task.is_terminal():
                continue
            missing_deps = [dep for dep in task.deps if dep not in self.completed]
            if missing_deps:
                blockers[task.id] = missing_deps
        return blockers

    def state_summary(self) -> dict:
        """Current state summary."""
        status_counts = {}
        for task in self.tasks.values():
            s = task.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            "mode": self.mode.value,
            "total": len(self.tasks),
            "completed": len(self.completed),
            "status_counts": status_counts,
            "blockers": self.detect_blockers(),
        }
