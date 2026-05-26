from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
import uuid
import time


class AdapterStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    task_id: str
    adapter_id: str
    status: AdapterStatus
    output: str
    duration_ms: float


class AgentAdapter(ABC):
    """Base adapter contract. All adapters implement this."""

    @abstractmethod
    def adapter_id(self) -> str: ...

    @abstractmethod
    def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        """Submit task. Returns request_id."""

    @abstractmethod
    def poll(self, request_id: str) -> TaskResult:
        """Poll task status."""

    @abstractmethod
    def cancel(self, request_id: str) -> bool:
        """Cancel running task."""

    @abstractmethod
    def status(self) -> dict:
        """Adapter-level status."""


class MockAdapter(AgentAdapter):
    """Simulated adapter. No real API calls."""

    def __init__(self, adapter_id: str = "mock", auto_complete: bool = True):
        self._adapter_id = adapter_id
        self._auto_complete = auto_complete
        self._tasks: dict[str, dict] = {}
        self._submitted = 0
        self._cancelled = 0

    def adapter_id(self) -> str:
        return self._adapter_id

    def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        request_id = str(uuid.uuid4())
        self._tasks[request_id] = {
            "task_id": task_id,
            "prompt": prompt,
            "kwargs": kwargs,
            "submitted_at": time.time(),
        }
        self._submitted += 1
        return request_id

    def poll(self, request_id: str) -> TaskResult:
        if request_id not in self._tasks:
            raise KeyError(f"Unknown request_id: {request_id}")
        task = self._tasks[request_id]
        duration = (time.time() - task["submitted_at"]) * 1000
        status = AdapterStatus.COMPLETED if self._auto_complete else AdapterStatus.RUNNING
        return TaskResult(
            task_id=task["task_id"],
            adapter_id=self._adapter_id,
            status=status,
            output="mock output",
            duration_ms=duration,
        )

    def cancel(self, request_id: str) -> bool:
        if request_id not in self._tasks:
            return False
        self._cancelled += 1
        return True

    def status(self) -> dict:
        return {
            "adapter_id": self._adapter_id,
            "submitted": self._submitted,
            "cancelled": self._cancelled,
            "running": len(self._tasks) - self._cancelled,
        }


class ClaudeAdapter(AgentAdapter):
    """Placeholder for future Claude integration. Raises NotImplementedError."""

    def adapter_id(self) -> str:
        raise NotImplementedError

    def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    def poll(self, request_id: str) -> TaskResult:
        raise NotImplementedError

    def cancel(self, request_id: str) -> bool:
        raise NotImplementedError

    def status(self) -> dict:
        raise NotImplementedError


class MiMoAdapter(AgentAdapter):
    """Placeholder for future MiMo integration. Raises NotImplementedError."""

    def adapter_id(self) -> str:
        raise NotImplementedError

    def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    def poll(self, request_id: str) -> TaskResult:
        raise NotImplementedError

    def cancel(self, request_id: str) -> bool:
        raise NotImplementedError

    def status(self) -> dict:
        raise NotImplementedError


class CodexAdapter(AgentAdapter):
    """Placeholder for future Codex integration. Raises NotImplementedError."""

    def adapter_id(self) -> str:
        raise NotImplementedError

    def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    def poll(self, request_id: str) -> TaskResult:
        raise NotImplementedError

    def cancel(self, request_id: str) -> bool:
        raise NotImplementedError

    def status(self) -> dict:
        raise NotImplementedError
