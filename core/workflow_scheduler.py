"""Workflow Scheduler — DAG scheduling with simulated worker pool.

Simulation only. No real execution.
"""
from __future__ import annotations

from core.agent_factory import AgentFactory, ExecutionMode, Task, TaskStatus
from core.worker_pool import WorkerPool
from core.governance_state import GovernanceStateMachine, State


class WorkflowScheduler:
    def __init__(self, max_workers: int = 5, mode: ExecutionMode = ExecutionMode.DAG):
        self.factory = AgentFactory(mode=mode)
        self.worker_pool = WorkerPool(max_workers=max_workers)
        self.state_machine = GovernanceStateMachine()
        self.execution_log: list[dict] = []

    def load_tasks(self, task_specs: list[dict]) -> None:
        for spec in task_specs:
            task_id = spec["id"]
            deps = spec.get("deps", [])
            self.factory.register(Task(id=task_id, deps=deps))
            self.state_machine.register(task_id, deps)

    def schedule_step(self) -> dict:
        """One scheduling step: find ready tasks, assign to workers."""
        ready = [tid for tid, t in self.factory.tasks.items()
                 if t.is_ready(self.factory.completed)]

        running = {w.current_task for w in self.worker_pool.busy_workers() if w.current_task}
        dispatchable = [tid for tid in ready if tid not in running]

        assigned = []
        for task_id in dispatchable:
            if self.worker_pool.can_assign():
                assignment = self.worker_pool.assign(task_id)
                if assignment:
                    self.state_machine.transition(task_id, State.READY, "deps met")
                    self.state_machine.transition(task_id, State.RUNNING, f"assigned to {assignment.worker_id}")
                    assigned.append(task_id)

        blocked = [tid for tid in dispatchable if tid not in assigned]

        return {
            "ready": ready,
            "assigned": assigned,
            "blocked_by_capacity": blocked,
            "worker_status": self.worker_pool.status(),
        }

    def complete_task(self, task_id: str, status: TaskStatus = TaskStatus.PASS) -> dict:
        self.factory.execute_task(task_id, status)
        worker = self.worker_pool.complete(task_id)

        if status == TaskStatus.PASS:
            self.state_machine.transition(task_id, State.PASS, "completed")
        elif status == TaskStatus.FAIL:
            self.state_machine.transition(task_id, State.FAIL, "failed")

        self.execution_log.append({
            "task": task_id,
            "status": status.value,
            "worker": worker.id if worker else None,
        })

        return {
            "task": task_id,
            "status": status.value,
            "worker_released": worker.id if worker else None,
            "newly_ready": self.state_machine.resolve_ready(),
        }

    def is_complete(self) -> bool:
        return all(t.is_terminal() for t in self.factory.tasks.values())

    def run_to_completion(self) -> list[dict]:
        """Simulate full execution."""
        steps = []
        while not self.is_complete():
            step = self.schedule_step()

            for task_id in step["assigned"]:
                self.complete_task(task_id, TaskStatus.PASS)

            steps.append(step)

            if len(steps) > 100:
                break

        return steps

    def summary(self) -> dict:
        status_counts = {}
        for task in self.factory.tasks.values():
            s = task.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            "total_tasks": len(self.factory.tasks),
            "completed": len(self.factory.completed),
            "status_counts": status_counts,
            "steps_taken": len(self.execution_log),
            "worker_status": self.worker_pool.status(),
            "is_complete": self.is_complete(),
        }
