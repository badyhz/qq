"""Runtime budget attribution — per-task, per-adapter, per-workflow cost tracking."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaskCost:
    task_id: str
    adapter_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: float


@dataclass
class AdapterCost:
    adapter_id: str
    total_tasks: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0


@dataclass
class WorkflowCost:
    workflow_id: str
    total_tasks: int = 0
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    adapter_breakdown: dict[str, AdapterCost] = field(default_factory=dict)


class RuntimeBudgetAttribution:
    """Tracks and attributes costs in workflow runtime."""

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, TaskCost]] = defaultdict(dict)

    def record_task_cost(
        self,
        workflow_id: str,
        task_id: str,
        adapter_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> TaskCost:
        tc = TaskCost(
            task_id=task_id,
            adapter_id=adapter_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            timestamp=time.time(),
        )
        self._tasks[workflow_id][task_id] = tc
        return tc

    def get_task_cost(self, workflow_id: str, task_id: str) -> Optional[TaskCost]:
        return self._tasks.get(workflow_id, {}).get(task_id)

    def get_adapter_costs(self, workflow_id: str, adapter_id: str) -> AdapterCost:
        ac = AdapterCost(adapter_id=adapter_id)
        for tc in self._tasks.get(workflow_id, {}).values():
            if tc.adapter_id == adapter_id:
                ac.total_tasks += 1
                ac.total_input_tokens += tc.input_tokens
                ac.total_output_tokens += tc.output_tokens
                ac.total_cost_usd += tc.cost_usd
        return ac

    def get_workflow_cost(self, workflow_id: str) -> WorkflowCost:
        wc = WorkflowCost(workflow_id=workflow_id)
        adapter_map: dict[str, AdapterCost] = {}
        for tc in self._tasks.get(workflow_id, {}).values():
            wc.total_tasks += 1
            wc.total_cost_usd += tc.cost_usd
            wc.total_input_tokens += tc.input_tokens
            wc.total_output_tokens += tc.output_tokens
            if tc.adapter_id not in adapter_map:
                adapter_map[tc.adapter_id] = AdapterCost(adapter_id=tc.adapter_id)
            ac = adapter_map[tc.adapter_id]
            ac.total_tasks += 1
            ac.total_input_tokens += tc.input_tokens
            ac.total_output_tokens += tc.output_tokens
            ac.total_cost_usd += tc.cost_usd
        wc.adapter_breakdown = adapter_map
        return wc

    def get_all_adapter_costs(self, workflow_id: str) -> dict[str, AdapterCost]:
        result: dict[str, AdapterCost] = {}
        for tc in self._tasks.get(workflow_id, {}).values():
            if tc.adapter_id not in result:
                result[tc.adapter_id] = AdapterCost(adapter_id=tc.adapter_id)
            ac = result[tc.adapter_id]
            ac.total_tasks += 1
            ac.total_input_tokens += tc.input_tokens
            ac.total_output_tokens += tc.output_tokens
            ac.total_cost_usd += tc.cost_usd
        return result

    def list_workflows(self) -> list[str]:
        return list(self._tasks.keys())

    def clear_workflow(self, workflow_id: str) -> None:
        self._tasks.pop(workflow_id, None)

    def summary(self) -> dict:
        total_tasks = 0
        total_cost = 0.0
        total_in = 0
        total_out = 0
        adapters_seen: set[str] = set()
        for wf_tasks in self._tasks.values():
            for tc in wf_tasks.values():
                total_tasks += 1
                total_cost += tc.cost_usd
                total_in += tc.input_tokens
                total_out += tc.output_tokens
                adapters_seen.add(tc.adapter_id)
        return {
            "total_workflows": len(self._tasks),
            "total_tasks": total_tasks,
            "total_cost_usd": total_cost,
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "unique_adapters": len(adapters_seen),
        }
