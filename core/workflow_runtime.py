"""Workflow Runtime — unified runtime connecting scheduler, workers, governance, and safety."""
from __future__ import annotations

from core.agent_factory import ExecutionMode, TaskStatus
from core.governance_state import State
from core.workflow_safety import WorkflowSafetyValidator
from core.workflow_scheduler import WorkflowScheduler


class WorkflowRuntime:
    """Unified runtime connecting scheduler, workers, governance, and safety."""

    def __init__(self, max_workers: int = 5, mode: str = "DAG"):
        exec_mode = ExecutionMode.DAG if mode == "DAG" else ExecutionMode.QUEUE
        self.scheduler = WorkflowScheduler(max_workers=max_workers, mode=exec_mode)
        self.safety = WorkflowSafetyValidator()
        self.execution_log: list[dict] = []
        self._mode = mode

    def load_workflow(self, tasks: list[dict], workflow_id: str = "default") -> dict:
        """Load tasks, validate safety, return validation result."""
        violations = self.safety.validate_workflow({"tasks": tasks, "mode": self._mode})
        if violations:
            return {"valid": False, "violations": [v.detail for v in violations]}

        self.scheduler.load_tasks(tasks)
        return {"valid": True, "workflow_id": workflow_id, "task_count": len(tasks)}

    def run(self) -> dict:
        """Execute all tasks through scheduler. Returns summary."""
        steps = self.scheduler.run_to_completion()
        self.execution_log.extend(self.scheduler.execution_log)
        return {
            "steps": len(steps),
            "total_tasks": len(self.scheduler.factory.tasks),
            "completed": len(self.scheduler.factory.completed),
            "is_complete": self.is_complete(),
        }

    def run_step(self) -> dict:
        """Execute one scheduling step."""
        step = self.scheduler.schedule_step()
        for task_id in step["assigned"]:
            result = self.scheduler.complete_task(task_id, TaskStatus.PASS)
            self.execution_log.append(result)
        return step

    def is_complete(self) -> bool:
        """Check if all tasks are done."""
        return self.scheduler.is_complete()

    def status(self) -> dict:
        """Full runtime status."""
        summary = self.scheduler.summary()
        summary["execution_log_length"] = len(self.execution_log)
        summary["safety_violations"] = self.safety.summary()
        return summary

    def governance_report(self) -> dict:
        """Report governance state of all tasks."""
        return self.scheduler.state_machine.state_summary()
