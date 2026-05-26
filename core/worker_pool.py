"""Worker Pool — slot-based concurrency tracker.

Simulation only. No real threads or processes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WorkerState(Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"


@dataclass
class Worker:
    id: str
    state: WorkerState = WorkerState.IDLE
    current_task: str | None = None

    def is_idle(self) -> bool:
        return self.state == WorkerState.IDLE

    def assign(self, task_id: str) -> None:
        self.state = WorkerState.BUSY
        self.current_task = task_id

    def release(self) -> None:
        self.state = WorkerState.IDLE
        self.current_task = None


@dataclass
class TaskAssignment:
    worker_id: str
    task_id: str


class WorkerPool:
    def __init__(self, max_workers: int = 1):
        self.max_workers = max_workers
        self.workers: list[Worker] = [
            Worker(id=f"W{i+1}") for i in range(max_workers)
        ]
        self.completed: list[str] = []

    def available_slots(self) -> int:
        return sum(1 for w in self.workers if w.is_idle())

    def can_assign(self) -> bool:
        return self.available_slots() > 0

    def idle_workers(self) -> list[Worker]:
        return [w for w in self.workers if w.is_idle()]

    def busy_workers(self) -> list[Worker]:
        return [w for w in self.workers if not w.is_idle()]

    def assign(self, task_id: str) -> TaskAssignment | None:
        for w in self.workers:
            if w.is_idle():
                w.assign(task_id)
                return TaskAssignment(worker_id=w.id, task_id=task_id)
        return None

    def complete(self, task_id: str) -> Worker | None:
        for w in self.workers:
            if w.current_task == task_id:
                w.release()
                self.completed.append(task_id)
                return w
        return None

    def status(self) -> dict:
        workers_info = {}
        for w in self.workers:
            workers_info[w.id] = {
                "state": w.state.value,
                "task": w.current_task,
            }
        return {
            "total_workers": self.max_workers,
            "busy": len(self.busy_workers()),
            "idle": self.available_slots(),
            "tasks_assigned": self.max_workers - self.available_slots(),
            "tasks_completed": len(self.completed),
            "workers": workers_info,
        }
