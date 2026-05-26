from dataclasses import dataclass, field
from enum import Enum


class BudgetExceeded(Exception):
    pass


class BudgetStatus(Enum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"


@dataclass
class CostEntry:
    task_id: str
    adapter_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: str


class WorkflowBudget:
    def __init__(self, max_tokens: int = 1_000_000, max_cost_usd: float = 100.0,
                 warning_threshold: float = 0.8):
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.warning_threshold = warning_threshold
        self._entries: list[CostEntry] = []
        self._total_tokens: int = 0
        self._total_cost: float = 0.0
        self._exceeded: bool = False

    def record(self, task_id: str, adapter_id: str, input_tokens: int,
               output_tokens: int, cost_usd: float) -> CostEntry:
        """Record cost. Raises BudgetExceeded if over limit."""
        from datetime import datetime, timezone
        entry = CostEntry(
            task_id=task_id,
            adapter_id=adapter_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        new_tokens = self._total_tokens + input_tokens + output_tokens
        new_cost = self._total_cost + cost_usd
        if new_tokens > self.max_tokens or new_cost > self.max_cost_usd:
            self._exceeded = True
            raise BudgetExceeded(
                f"Budget exceeded: tokens={new_tokens}/{self.max_tokens}, "
                f"cost=${new_cost:.4f}/${self.max_cost_usd:.2f}"
            )
        self._total_tokens = new_tokens
        self._total_cost = new_cost
        self._entries.append(entry)
        return entry

    def check(self) -> BudgetStatus:
        """Check current budget status."""
        if self._exceeded:
            return BudgetStatus.EXCEEDED
        token_pct = self._total_tokens / self.max_tokens if self.max_tokens else 0
        cost_pct = self._total_cost / self.max_cost_usd if self.max_cost_usd else 0
        pct = max(token_pct, cost_pct)
        if pct >= 1.0:
            return BudgetStatus.EXCEEDED
        if pct >= self.warning_threshold:
            return BudgetStatus.WARNING
        return BudgetStatus.OK

    def per_task_budget(self, task_id: str) -> dict:
        """Get budget consumed by a specific task."""
        entries = [e for e in self._entries if e.task_id == task_id]
        tokens = sum(e.input_tokens + e.output_tokens for e in entries)
        cost = sum(e.cost_usd for e in entries)
        return {"task_id": task_id, "entries": len(entries), "tokens": tokens, "cost_usd": cost}

    def per_adapter_budget(self, adapter_id: str) -> dict:
        """Get budget consumed by a specific adapter."""
        entries = [e for e in self._entries if e.adapter_id == adapter_id]
        tokens = sum(e.input_tokens + e.output_tokens for e in entries)
        cost = sum(e.cost_usd for e in entries)
        return {"adapter_id": adapter_id, "entries": len(entries), "tokens": tokens, "cost_usd": cost}

    def is_exceeded(self) -> bool:
        """Check if budget exceeded."""
        return self._exceeded

    def remaining(self) -> dict:
        """Remaining budget."""
        return {
            "tokens": max(0, self.max_tokens - self._total_tokens),
            "cost_usd": round(max(0, self.max_cost_usd - self._total_cost), 6),
        }

    def summary(self) -> dict:
        """Full budget summary."""
        return {
            "total_entries": len(self._entries),
            "total_tokens": self._total_tokens,
            "total_cost_usd": self._total_cost,
            "max_tokens": self.max_tokens,
            "max_cost_usd": self.max_cost_usd,
            "status": self.check().value,
            "exceeded": self._exceeded,
        }

    def reset(self) -> None:
        """Reset all tracking."""
        self._entries.clear()
        self._total_tokens = 0
        self._total_cost = 0.0
        self._exceeded = False
