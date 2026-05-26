"""Sandbox-only MiMo adapter. No real endpoint usage. No API calls. No network."""

import asyncio
import random
import time
import uuid

from core.async_agent_adapter import (
    AsyncAgentAdapter,
    AsyncAdapterStatus,
    AsyncTaskResult,
)


class MiMoSandboxAdapter(AsyncAgentAdapter):
    """Simulated MiMo adapter for sandbox/testing. No network calls."""

    def __init__(
        self,
        model: str = "mimo-v2.5",
        fail_prob: float = 0.0,
        latency_ms: float = 30.0,
        max_retries: int = 3,
    ):
        self._model = model
        self._fail_prob = fail_prob
        self._latency_ms = latency_ms
        self._max_retries = max_retries
        self._tasks: dict[str, dict] = {}
        self._submitted = 0
        self._cancelled = 0
        self._failed = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._retry_count = 0
        self._success_after_retry = 0

    def adapter_id(self) -> str:
        return "mimo_sandbox"

    async def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        await asyncio.sleep(self._latency_ms / 1000)

        if self._fail_prob > 0.0 and random.random() < self._fail_prob:
            request_id = str(uuid.uuid4())
            self._tasks[request_id] = {
                "task_id": task_id,
                "prompt": prompt,
                "kwargs": kwargs,
                "submitted_at": time.time(),
                "status": AsyncAdapterStatus.FAILED,
                "fail_checked": True,
            }
            self._submitted += 1
            self._failed += 1
            return request_id

        request_id = str(uuid.uuid4())
        self._tasks[request_id] = {
            "task_id": task_id,
            "prompt": prompt,
            "kwargs": kwargs,
            "submitted_at": time.time(),
            "status": AsyncAdapterStatus.RUNNING,
            "retries": 0,
        }
        self._submitted += 1
        return request_id

    async def poll(self, request_id: str) -> AsyncTaskResult:
        if request_id not in self._tasks:
            raise KeyError(f"Unknown request_id: {request_id}")

        task = self._tasks[request_id]
        duration = (time.time() - task["submitted_at"]) * 1000

        if task["status"] == AsyncAdapterStatus.CANCELLED:
            return AsyncTaskResult(
                task_id=task["task_id"],
                adapter_id=self.adapter_id(),
                status=AsyncAdapterStatus.CANCELLED,
                output="",
                duration_ms=duration,
            )

        if task["status"] == AsyncAdapterStatus.FAILED:
            return AsyncTaskResult(
                task_id=task["task_id"],
                adapter_id=self.adapter_id(),
                status=AsyncAdapterStatus.FAILED,
                output="",
                duration_ms=duration,
            )

        # Random failure on first poll
        if (
            task["status"] == AsyncAdapterStatus.RUNNING
            and self._fail_prob > 0.0
            and not task.get("fail_checked", False)
        ):
            task["fail_checked"] = True
            if random.random() < self._fail_prob:
                retries = task.get("retries", 0)
                if retries < self._max_retries:
                    # Retry
                    task["retries"] = retries + 1
                    task["status"] = AsyncAdapterStatus.RUNNING
                    task["fail_checked"] = False
                    self._retry_count += 1
                    return AsyncTaskResult(
                        task_id=task["task_id"],
                        adapter_id=self.adapter_id(),
                        status=AsyncAdapterStatus.RUNNING,
                        output="",
                        duration_ms=duration,
                    )
                else:
                    task["status"] = AsyncAdapterStatus.FAILED
                    self._failed += 1
                    self._retry_count += 1
                    return AsyncTaskResult(
                        task_id=task["task_id"],
                        adapter_id=self.adapter_id(),
                        status=AsyncAdapterStatus.FAILED,
                        output="",
                        duration_ms=duration,
                    )

        # Complete
        task["status"] = AsyncAdapterStatus.COMPLETED
        prompt = task["prompt"]
        input_tokens = len(prompt) // 4
        output_tokens = 40
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        if task.get("retries", 0) > 0:
            self._success_after_retry += 1

        content = f"{self._model} sandbox response"
        return AsyncTaskResult(
            task_id=task["task_id"],
            adapter_id=self.adapter_id(),
            status=AsyncAdapterStatus.COMPLETED,
            output=content,
            duration_ms=duration,
        )

    async def cancel(self, request_id: str) -> bool:
        if request_id not in self._tasks:
            return False
        self._tasks[request_id]["status"] = AsyncAdapterStatus.CANCELLED
        self._cancelled += 1
        return True

    async def status(self) -> dict:
        running = self._submitted - self._cancelled - self._failed
        return {
            "adapter_id": self.adapter_id(),
            "model": self._model,
            "submitted": self._submitted,
            "cancelled": self._cancelled,
            "failed": self._failed,
            "running": running,
        }

    def token_summary(self) -> dict:
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
        }

    def retry_stats(self) -> dict:
        return {
            "retry_count": self._retry_count,
            "success_after_retry": self._success_after_retry,
        }
