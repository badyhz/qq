"""MiMo real API adapter skeleton. Dry-run only. No network calls."""

import asyncio
import logging
import time
import uuid
from typing import Any

from core.async_agent_adapter import (
    AsyncAgentAdapter,
    AsyncAdapterStatus,
    AsyncTaskResult,
)

logger = logging.getLogger(__name__)


class MiMoAPIAdapter(AsyncAgentAdapter):
    """Skeleton adapter structured for real MiMo API calls.

    Operates in dry-run mode by default:
    - All requests stored locally, never sent
    - All responses simulated
    - API key accepted but never used
    - Network calls impossible
    """

    def __init__(
        self,
        model: str = "mimo-v2.5",
        base_url: str = "https://api.mimo.example.com",
        api_key: str = None,
        max_retries: int = 3,
        budget_ceiling_usd: float = 10.0,
    ):
        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        self._max_retries = max_retries
        self._budget_ceiling_usd = budget_ceiling_usd
        self._dry_run = True

        # Task tracking
        self._tasks: dict[str, dict] = {}
        self._submitted = 0
        self._cancelled = 0
        self._failed = 0
        self._completed = 0

    def adapter_id(self) -> str:
        return "mimo_api"

    async def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        """Submit task. In skeleton mode, stores locally without sending."""
        await asyncio.sleep(0)

        # Pre-flight checks
        if not self.check_rate_limit():
            raise RuntimeError("Rate limit exceeded")
        if self.check_kill_switch():
            raise RuntimeError("Kill switch is active")

        request_id = str(uuid.uuid4())
        payload = self.build_request_payload(task_id, prompt, **kwargs)

        self._tasks[request_id] = {
            "task_id": task_id,
            "prompt": prompt,
            "kwargs": kwargs,
            "payload": payload,
            "submitted_at": time.time(),
            "status": AsyncAdapterStatus.RUNNING,
            "retries": 0,
        }
        self._submitted += 1

        logger.info(
            "[DRY-RUN] Task %s stored as request %s (no API call made)",
            task_id,
            request_id,
        )
        return request_id

    async def poll(self, request_id: str) -> AsyncTaskResult:
        """Poll task status. Returns simulated result in skeleton mode."""
        await asyncio.sleep(0)
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

        # Simulate completion in dry-run
        task["status"] = AsyncAdapterStatus.COMPLETED
        self._completed += 1

        raw_response = {
            "choices": [
                {
                    "message": {
                        "content": f"[DRY-RUN] {self._model} simulated response for task {task['task_id']}",
                        "role": "assistant",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": len(task["prompt"]) // 4,
                "completion_tokens": 42,
                "total_tokens": len(task["prompt"]) // 4 + 42,
            },
        }
        normalized = self.normalize_response(raw_response)

        return AsyncTaskResult(
            task_id=task["task_id"],
            adapter_id=self.adapter_id(),
            status=AsyncAdapterStatus.COMPLETED,
            output=normalized["output"],
            duration_ms=duration,
        )

    async def cancel(self, request_id: str) -> bool:
        """Cancel a task."""
        await asyncio.sleep(0)
        if request_id not in self._tasks:
            return False
        task = self._tasks[request_id]
        if task["status"] in (
            AsyncAdapterStatus.COMPLETED,
            AsyncAdapterStatus.FAILED,
            AsyncAdapterStatus.CANCELLED,
        ):
            return False
        task["status"] = AsyncAdapterStatus.CANCELLED
        self._cancelled += 1
        return True

    async def status(self) -> dict:
        """Return adapter stats."""
        await asyncio.sleep(0)
        return {
            "adapter_id": self.adapter_id(),
            "model": self._model,
            "base_url": self._base_url,
            "dry_run": self._dry_run,
            "api_key_set": self._api_key is not None,
            "submitted": self._submitted,
            "completed": self._completed,
            "cancelled": self._cancelled,
            "failed": self._failed,
            "budget_ceiling_usd": self._budget_ceiling_usd,
        }

    # -- Skeleton hooks -------------------------------------------------

    def build_request_payload(self, task_id: str, prompt: str, **kwargs) -> dict:
        """Build MiMo API request payload. Not sent in dry-run mode."""
        return {
            "model": self._model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "parameters": {
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1024),
                "top_p": kwargs.get("top_p", 0.9),
            },
            "metadata": {
                "task_id": task_id,
                "dry_run": self._dry_run,
            },
        }

    def normalize_response(self, raw_response: dict) -> dict:
        """Normalize raw API response to standard format."""
        choices = raw_response.get("choices", [])
        if not choices:
            return {"output": "", "usage": raw_response.get("usage", {})}

        message = choices[0].get("message", {})
        return {
            "output": message.get("content", ""),
            "usage": raw_response.get("usage", {}),
        }

    def check_rate_limit(self) -> bool:
        """Hook for rate limiting. Returns True in skeleton."""
        return True

    def check_budget(self, cost_usd: float) -> bool:
        """Hook for budget checking. Returns True in skeleton if under ceiling."""
        return cost_usd <= self._budget_ceiling_usd

    def check_kill_switch(self) -> bool:
        """Hook for kill switch. Returns False in skeleton."""
        return False

    def set_api_key(self, api_key: str) -> None:
        """Store API key. Never logged or exposed."""
        self._api_key = api_key
        logger.info("API key set: %s", self.mask_key(api_key))

    def mask_key(self, key: str) -> str:
        """Return masked version of API key."""
        if key is None:
            return "<none>"
        if len(key) <= 8:
            return "*" * len(key)
        return key[:4] + "*" * (len(key) - 8) + key[-4:]

    def retry_handler(self, error: Exception) -> bool:
        """Determine if error is retryable. Skeleton always returns True."""
        return True
