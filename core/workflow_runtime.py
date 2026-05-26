"""Workflow Runtime — unified runtime with scheduler, workers, governance, safety,
async adapters, budget tracking, retry policy, circuit breaker, and observability."""
from __future__ import annotations

import asyncio
from typing import Optional

from core.agent_factory import ExecutionMode, TaskStatus
from core.governance_state import State
from core.workflow_safety import WorkflowSafetyValidator
from core.workflow_scheduler import WorkflowScheduler
from core.async_agent_adapter import AsyncAgentAdapter, AsyncMockAdapter, AsyncTaskResult, AsyncAdapterStatus
from core.workflow_budget import WorkflowBudget, BudgetExceeded, BudgetStatus
from core.workflow_retry_policy import RetryPolicy, TaskRetryState, FailureType
from core.workflow_circuit_breaker import CircuitBreaker, CircuitState
from core.workflow_observability import WorkflowObservability, EventType


class WorkflowRuntime:
    """Unified runtime connecting scheduler, workers, governance, safety,
    async adapters, budget, retry, circuit breaker, and observability."""

    def __init__(
        self,
        max_workers: int = 5,
        mode: str = "DAG",
        budget: Optional[WorkflowBudget] = None,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        exec_mode = ExecutionMode.DAG if mode == "DAG" else ExecutionMode.QUEUE
        self.scheduler = WorkflowScheduler(max_workers=max_workers, mode=exec_mode)
        self.safety = WorkflowSafetyValidator()
        self.budget = budget or WorkflowBudget()
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.observability = WorkflowObservability()
        self.execution_log: list[dict] = []
        self._mode = mode
        self._retry_states: dict[str, TaskRetryState] = {}
        self._adapter: Optional[AsyncAgentAdapter] = None

    def set_adapter(self, adapter: AsyncAgentAdapter) -> None:
        self._adapter = adapter

    def load_workflow(self, tasks: list[dict], workflow_id: str = "default") -> dict:
        violations = self.safety.validate_workflow({"tasks": tasks, "mode": self._mode})
        if violations:
            for v in violations:
                self.observability.emit(EventType.SAFETY_VIOLATION, metadata={"detail": v.detail})
            return {"valid": False, "violations": [v.detail for v in violations]}

        self.scheduler.load_tasks(tasks)
        self.observability.emit(EventType.WORKFLOW_STARTED, metadata={
            "workflow_id": workflow_id, "task_count": len(tasks),
        })
        return {"valid": True, "workflow_id": workflow_id, "task_count": len(tasks)}

    def run(self) -> dict:
        self.observability.emit(EventType.WORKFLOW_STARTED)
        steps = self.scheduler.run_to_completion()
        self.execution_log.extend(self.scheduler.execution_log)

        for entry in self.execution_log:
            self.observability.emit(
                EventType.TASK_COMPLETED if entry.get("status") == "PASS" else EventType.TASK_FAILED,
                task_id=entry.get("task", ""),
            )

        self.observability.emit(EventType.WORKFLOW_COMPLETED)
        return {
            "steps": len(steps),
            "total_tasks": len(self.scheduler.factory.tasks),
            "completed": len(self.scheduler.factory.completed),
            "is_complete": self.is_complete(),
            "budget_status": self.budget.check().value,
            "circuit_state": self.circuit_breaker.state.value,
            "observability_summary": self.observability.summary(),
        }

    def run_step(self) -> dict:
        step = self.scheduler.schedule_step()
        for task_id in step["assigned"]:
            self.observability.emit(EventType.TASK_STARTED, task_id=task_id)

            if self.circuit_breaker.state == CircuitState.OPEN:
                self.observability.emit(EventType.TASK_BLOCKED, task_id=task_id, reason="circuit_open")
                continue

            result = self.scheduler.complete_task(task_id, TaskStatus.PASS)
            self.execution_log.append(result)
            self.circuit_breaker.record_success()
            self.observability.emit(EventType.TASK_COMPLETED, task_id=task_id)
        return step

    async def run_async(self, adapter: Optional[AsyncAgentAdapter] = None) -> dict:
        adapter = adapter or self._adapter or AsyncMockAdapter()
        self.observability.emit(EventType.WORKFLOW_STARTED)

        while not self.is_complete():
            step = self.scheduler.schedule_step()
            for task_id in step["assigned"]:
                self.observability.emit(EventType.TASK_STARTED, task_id=task_id)

                if self.circuit_breaker.state == CircuitState.OPEN:
                    self.observability.emit(EventType.TASK_BLOCKED, task_id=task_id, reason="circuit_open")
                    continue

                success = await self._execute_with_retry(adapter, task_id)
                if not success:
                    self.circuit_breaker.record_failure(f"task_{task_id}_failed")
                    self.observability.emit(EventType.TASK_FAILED, task_id=task_id)
                    if self.circuit_breaker.state == CircuitState.OPEN:
                        self.observability.emit(EventType.CIRCUIT_OPENED)

        self.observability.emit(EventType.WORKFLOW_COMPLETED)
        return self._build_summary()

    async def _execute_with_retry(self, adapter: AsyncAgentAdapter, task_id: str) -> bool:
        retry_state = self._retry_states.setdefault(task_id, TaskRetryState(task_id=task_id))

        while retry_state.can_retry(self.retry_policy):
            try:
                request_id = await adapter.submit_task(task_id, f"execute {task_id}")
                result = await adapter.poll(request_id)

                if result.status == AsyncAdapterStatus.COMPLETED:
                    self.scheduler.complete_task(task_id, TaskStatus.PASS)
                    self.circuit_breaker.record_success()
                    self.observability.emit(EventType.TASK_COMPLETED, task_id=task_id)
                    return True
                elif result.status == AsyncAdapterStatus.FAILED:
                    failure = self.retry_policy.classify_failure(result.output)
                    retry_state.record_failure(failure, self.retry_policy)
                    self.observability.emit(EventType.TASK_FAILED, task_id=task_id,
                                            failure=failure.value, attempt=retry_state.attempt)
                else:
                    break
            except Exception as exc:
                failure = self.retry_policy.classify_failure(str(exc))
                retry_state.record_failure(failure, self.retry_policy)
                self.observability.emit(EventType.TASK_FAILED, task_id=task_id,
                                        error=str(exc), attempt=retry_state.attempt)

        self.scheduler.complete_task(task_id, TaskStatus.FAIL)
        return False

    def record_budget(self, task_id: str, adapter_id: str, input_tokens: int,
                      output_tokens: int, cost_usd: float) -> None:
        try:
            self.budget.record(task_id, adapter_id, input_tokens, output_tokens, cost_usd)
        except BudgetExceeded:
            self.observability.emit(EventType.BUDGET_EXCEEDED, task_id=task_id,
                                    cost_usd=cost_usd, total=self.budget._total_cost)
            self.circuit_breaker.record_failure("budget_exceeded")

    def is_complete(self) -> bool:
        return self.scheduler.is_complete()

    def status(self) -> dict:
        summary = self.scheduler.summary()
        summary["execution_log_length"] = len(self.execution_log)
        summary["safety_violations"] = self.safety.summary()
        summary["budget"] = self.budget.summary()
        summary["circuit_breaker"] = self.circuit_breaker.summary()
        summary["observability"] = self.observability.summary()
        summary["retry_states"] = {
            k: {"attempts": v.attempt, "last_failure": v.last_failure.value if v.last_failure else None}
            for k, v in self._retry_states.items()
        }
        return summary

    def governance_report(self) -> dict:
        return self.scheduler.state_machine.state_summary()

    def _build_summary(self) -> dict:
        return {
            "total_tasks": len(self.scheduler.factory.tasks),
            "completed": len(self.scheduler.factory.completed),
            "is_complete": self.is_complete(),
            "budget_status": self.budget.check().value,
            "circuit_state": self.circuit_breaker.state.value,
            "observability_summary": self.observability.summary(),
        }
