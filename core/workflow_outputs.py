"""Workflow Output Bus — task→task data passing in workflow runtime."""

import time
from enum import Enum
from typing import Any


class MissingOutputError(Exception):
    """Raised when consuming non-existent output."""


class OutputType(Enum):
    JSON = "json"
    TEXT = "text"
    BINARY = "binary"
    ERROR = "error"


class WorkflowOutputBus:
    """Scoped store for task outputs within workflows."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, dict[str, Any]]] = {}

    def publish_output(
        self,
        workflow_id: str,
        task_id: str,
        output: dict,
        output_type: OutputType = OutputType.JSON,
    ) -> None:
        if workflow_id not in self._store:
            self._store[workflow_id] = {}
        self._store[workflow_id][task_id] = {
            "task_id": task_id,
            "output_type": output_type,
            "data": output,
            "timestamp": time.time(),
        }

    def consume_output(self, workflow_id: str, task_id: str) -> dict:
        try:
            return self._store[workflow_id][task_id]
        except KeyError:
            raise MissingOutputError(
                f"No output for workflow={workflow_id!r} task={task_id!r}"
            )

    def has_output(self, workflow_id: str, task_id: str) -> bool:
        return workflow_id in self._store and task_id in self._store[workflow_id]

    def list_outputs(self, workflow_id: str) -> dict[str, dict]:
        return dict(self._store.get(workflow_id, {}))

    def clear_workflow(self, workflow_id: str) -> None:
        self._store.pop(workflow_id, None)

    def summary(self) -> dict:
        total_outputs = sum(len(tasks) for tasks in self._store.values())
        return {
            "total_workflows": len(self._store),
            "total_outputs": total_outputs,
            "per_workflow": {wf: len(tasks) for wf, tasks in self._store.items()},
        }
