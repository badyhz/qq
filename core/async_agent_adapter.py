import asyncio
import random
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass


class AsyncAdapterStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTaskResult:
    task_id: str
    adapter_id: str
    status: AsyncAdapterStatus
    output: str
    duration_ms: float


class AsyncAgentAdapter(ABC):
    """Base async adapter contract. All async adapters implement this."""

    @abstractmethod
    def adapter_id(self) -> str: ...

    @abstractmethod
    async def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        """Submit task async. Returns request_id."""

    @abstractmethod
    async def poll(self, request_id: str) -> AsyncTaskResult:
        """Poll task status async."""

    @abstractmethod
    async def cancel(self, request_id: str) -> bool:
        """Cancel running task async."""

    @abstractmethod
    async def status(self) -> dict:
        """Adapter-level status async."""


class AsyncMockAdapter(AsyncAgentAdapter):
    """Simulated async adapter. No real API calls."""

    def __init__(
        self,
        adapter_id: str = "async_mock",
        auto_complete: bool = True,
        fail_prob: float = 0.0,
    ):
        self._adapter_id = adapter_id
        self._auto_complete = auto_complete
        self._fail_prob = fail_prob
        self._tasks: dict[str, dict] = {}
        self._submitted = 0
        self._cancelled = 0
        self._failed = 0

    def adapter_id(self) -> str:
        return self._adapter_id

    async def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        await asyncio.sleep(0)
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
        elif self._auto_complete:
            status = AsyncAdapterStatus.COMPLETED
        else:
            status = AsyncAdapterStatus.RUNNING

        # Check for random failure on first poll if auto_complete and fail_prob > 0
        if (
            status == AsyncAdapterStatus.COMPLETED
            and self._fail_prob > 0.0
            and not task.get("fail_checked", False)
        ):
            task["fail_checked"] = True
            if random.random() < self._fail_prob:
                task["status"] = AsyncAdapterStatus.FAILED
                self._failed += 1
                status = AsyncAdapterStatus.FAILED

        return AsyncTaskResult(
            task_id=task["task_id"],
            adapter_id=self._adapter_id,
            status=status,
            output="mock output",
            duration_ms=duration,
        )

    async def cancel(self, request_id: str) -> bool:
        await asyncio.sleep(0)
        if request_id not in self._tasks:
            return False
        self._tasks[request_id]["status"] = AsyncAdapterStatus.CANCELLED
        self._cancelled += 1
        return True

    async def status(self) -> dict:
        await asyncio.sleep(0)
        return {
            "adapter_id": self._adapter_id,
            "submitted": self._submitted,
            "cancelled": self._cancelled,
            "failed": self._failed,
            "running": self._submitted - self._cancelled - self._failed,
        }


class SyncToAsyncAdapter(AsyncAgentAdapter):
    """Wrap a sync AgentAdapter to work in async context."""

    def __init__(self, sync_adapter):
        self._sync = sync_adapter

    def adapter_id(self) -> str:
        return self._sync.adapter_id()

    async def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        return await asyncio.to_thread(self._sync.submit_task, task_id, prompt, **kwargs)

    async def poll(self, request_id: str) -> AsyncTaskResult:
        sync_result = await asyncio.to_thread(self._sync.poll, request_id)
        return AsyncTaskResult(
            task_id=sync_result.task_id,
            adapter_id=sync_result.adapter_id,
            status=AsyncAdapterStatus(sync_result.status.value),
            output=sync_result.output,
            duration_ms=sync_result.duration_ms,
        )

    async def cancel(self, request_id: str) -> bool:
        return await asyncio.to_thread(self._sync.cancel, request_id)

    async def status(self) -> dict:
        return await asyncio.to_thread(self._sync.status)
