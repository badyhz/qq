"""Sandbox-only Claude adapter. No API calls, no credentials, no network."""

import asyncio
import random
import time
import uuid

from core.async_agent_adapter import (
    AsyncAgentAdapter,
    AsyncAdapterStatus,
    AsyncTaskResult,
)


class ClaudeSandboxAdapter(AsyncAgentAdapter):
    """Simulated Claude adapter for sandbox/testing."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        fail_prob: float = 0.0,
        latency_ms: float = 50.0,
    ):
        self._model = model
        self._fail_prob = fail_prob
        self._latency_ms = latency_ms
        self._tasks: dict[str, dict] = {}
        self._submitted = 0
        self._completed = 0
        self._failed = 0
        self._cancelled = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def adapter_id(self) -> str:
        return "claude_sandbox"

    async def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        await asyncio.sleep(self._latency_ms / 1000)
        request_id = str(uuid.uuid4())
        self._tasks[request_id] = {
            "task_id": task_id,
            "prompt": prompt,
            "kwargs": kwargs,
            "submitted_at": time.time(),
            "status": AsyncAdapterStatus.RUNNING,
        }
        self._submitted += 1
        return request_id

    async def poll(self, request_id: str) -> AsyncTaskResult:
        await asyncio.sleep(0)
        if request_id not in self._tasks:
            raise KeyError(f"Unknown request_id: {request_id}")
        task = self._tasks[request_id]
        duration = (time.time() - task["submitted_at"]) * 1000

        if task["status"] == AsyncAdapterStatus.CANCELLED:
            status = AsyncAdapterStatus.CANCELLED
        elif task["status"] == AsyncAdapterStatus.FAILED:
            status = AsyncAdapterStatus.FAILED
        elif task["status"] == AsyncAdapterStatus.RUNNING:
            # First poll: check for random failure
            if (
                self._fail_prob > 0.0
                and not task.get("fail_checked", False)
            ):
                task["fail_checked"] = True
                if random.random() < self._fail_prob:
                    task["status"] = AsyncAdapterStatus.FAILED
                    self._failed += 1
                    status = AsyncAdapterStatus.FAILED
                else:
                    task["status"] = AsyncAdapterStatus.COMPLETED
                    self._completed += 1
                    status = AsyncAdapterStatus.COMPLETED
            else:
                task["status"] = AsyncAdapterStatus.COMPLETED
                self._completed += 1
                status = AsyncAdapterStatus.COMPLETED
        else:
            status = task["status"]

        output = ""
        if status == AsyncAdapterStatus.COMPLETED:
            prompt = task["prompt"]
            input_tokens = len(prompt) // 4
            output_tokens = 50
            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens
            import json
            output = json.dumps(
                {
                    "model": self._model,
                    "content": "sandbox response",
                    "tokens": {"input": input_tokens, "output": output_tokens},
                }
            )

        return AsyncTaskResult(
            task_id=task["task_id"],
            adapter_id="claude_sandbox",
            status=status,
            output=output,
            duration_ms=duration,
        )

    async def cancel(self, request_id: str) -> bool:
        await asyncio.sleep(0)
        if request_id not in self._tasks:
            return False
        task = self._tasks[request_id]
        if task["status"] == AsyncAdapterStatus.RUNNING:
            task["status"] = AsyncAdapterStatus.CANCELLED
            self._cancelled += 1
            return True
        return False

    async def status(self) -> dict:
        await asyncio.sleep(0)
        return {
            "adapter_id": "claude_sandbox",
            "submitted": self._submitted,
            "completed": self._completed,
            "failed": self._failed,
            "cancelled": self._cancelled,
        }

    def token_summary(self) -> dict:
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
        }
