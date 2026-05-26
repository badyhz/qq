"""Skeleton Claude API adapter. Structured for real API calls but runs in dry-run mode.

All requests are stored locally. No network calls are made.
API keys are accepted but never used.
"""

import asyncio
import time
import uuid
from typing import Any, Optional

from core.async_agent_adapter import (
    AsyncAgentAdapter,
    AsyncAdapterStatus,
    AsyncTaskResult,
)


class ClaudeAPIAdapter(AsyncAgentAdapter):
    """Real-API-shaped Claude adapter in dry-run mode.

    Skeleton: builds correct payloads, parses responses, tracks stats,
    but never sends anything over the network.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com",
        max_retries: int = 3,
        budget_ceiling_usd: float = 10.0,
    ):
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._max_retries = max_retries
        self._budget_ceiling_usd = budget_ceiling_usd
        self._dry_run = True

        # Request storage
        self._requests: dict[str, dict[str, Any]] = {}
        self._submitted = 0
        self._completed = 0
        self._failed = 0
        self._cancelled = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost_usd = 0.0

    # ── Adapter contract ──────────────────────────────────────────────

    def adapter_id(self) -> str:
        return "claude_api"

    async def submit_task(self, task_id: str, prompt: str, **kwargs) -> str:
        await asyncio.sleep(0)

        # Pre-flight hooks
        if self.check_kill_switch():
            raise RuntimeError("Kill switch active — refusing task")
        if not self.check_rate_limit():
            raise RuntimeError("Rate limit exceeded")

        request_id = str(uuid.uuid4())
        payload = self.build_request_payload(task_id, prompt, **kwargs)

        self._requests[request_id] = {
            "task_id": task_id,
            "prompt": prompt,
            "kwargs": kwargs,
            "payload": payload,
            "submitted_at": time.time(),
            "status": AsyncAdapterStatus.RUNNING,
            "response": None,
        }
        self._submitted += 1

        # Dry-run: simulate immediate completion
        input_tokens = len(prompt) // 4
        output_tokens = 50
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        raw_response = {
            "id": f"msg_{uuid.uuid4().hex[:24]}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "dry-run skeleton response"}],
            "model": self._model,
            "stop_reason": "end_turn",
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }
        parsed = self.parse_response(raw_response)
        self._requests[request_id]["response"] = parsed
        self._requests[request_id]["status"] = AsyncAdapterStatus.COMPLETED
        self._completed += 1

        return request_id

    async def poll(self, request_id: str) -> AsyncTaskResult:
        await asyncio.sleep(0)
        if request_id not in self._requests:
            raise KeyError(f"Unknown request_id: {request_id}")

        req = self._requests[request_id]
        duration = (time.time() - req["submitted_at"]) * 1000
        status = req["status"]

        output = ""
        if req["response"] is not None:
            import json
            output = json.dumps(req["response"])

        return AsyncTaskResult(
            task_id=req["task_id"],
            adapter_id="claude_api",
            status=status,
            output=output,
            duration_ms=duration,
        )

    async def cancel(self, request_id: str) -> bool:
        await asyncio.sleep(0)
        if request_id not in self._requests:
            return False
        req = self._requests[request_id]
        if req["status"] == AsyncAdapterStatus.RUNNING:
            req["status"] = AsyncAdapterStatus.CANCELLED
            self._cancelled += 1
            return True
        return False

    async def status(self) -> dict:
        await asyncio.sleep(0)
        return {
            "adapter_id": "claude_api",
            "model": self._model,
            "dry_run": self._dry_run,
            "base_url": self._base_url,
            "submitted": self._submitted,
            "completed": self._completed,
            "failed": self._failed,
            "cancelled": self._cancelled,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_cost_usd": self._total_cost_usd,
            "budget_ceiling_usd": self._budget_ceiling_usd,
        }

    # ── Payload / response helpers ────────────────────────────────────

    def build_request_payload(
        self, task_id: str, prompt: str, **kwargs
    ) -> dict[str, Any]:
        """Build a Claude API request payload (not sent in dry-run)."""
        max_tokens = kwargs.pop("max_tokens", 4096)
        system = kwargs.pop("system", None)
        temperature = kwargs.pop("temperature", 0.7)

        messages = [{"role": "user", "content": prompt}]

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "metadata": {"task_id": task_id},
        }
        if system is not None:
            payload["system"] = system
        payload.update(kwargs)
        return payload

    def parse_response(self, raw_response: dict) -> dict:
        """Normalize a Claude API response to a standard internal format."""
        content_parts = raw_response.get("content", [])
        text = ""
        if content_parts and isinstance(content_parts, list):
            text = content_parts[0].get("text", "")

        usage = raw_response.get("usage", {})
        cost = self._estimate_cost(
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
        )
        self._total_cost_usd += cost

        return {
            "id": raw_response.get("id", ""),
            "text": text,
            "model": raw_response.get("model", self._model),
            "stop_reason": raw_response.get("stop_reason", "unknown"),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "estimated_cost_usd": cost,
        }

    # ── Guard hooks ───────────────────────────────────────────────────

    def check_rate_limit(self) -> bool:
        """Hook for rate limiting. Returns True (allowed) in skeleton."""
        return True

    def check_budget(self, cost_usd: float) -> bool:
        """Hook for budget guard. Returns True if within budget."""
        return (self._total_cost_usd + cost_usd) <= self._budget_ceiling_usd

    def check_kill_switch(self) -> bool:
        """Hook for kill switch. Returns False (not killed) in skeleton."""
        return False

    # ── API key management ────────────────────────────────────────────

    def set_api_key(self, api_key: str) -> None:
        """Store API key. Never log or expose it."""
        self._api_key = api_key

    @staticmethod
    def mask_key(key: Optional[str]) -> str:
        """Return masked version of an API key."""
        if not key or len(key) < 8:
            return "****"
        return key[:3] + "..." + key[-3:]

    # ── Internal helpers ──────────────────────────────────────────────

    @staticmethod
    def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
        """Rough cost estimate for Sonnet-class model."""
        cost_per_1k_input = 0.003
        cost_per_1k_output = 0.015
        return (input_tokens / 1000 * cost_per_1k_input) + (
            output_tokens / 1000 * cost_per_1k_output
        )
