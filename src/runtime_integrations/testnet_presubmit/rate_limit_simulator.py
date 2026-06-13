"""Rate limit simulator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class RateLimitRule:
    rule_id: str
    max_requests_per_minute: int
    max_order_requests_per_minute: int
    cool_down_seconds: float
    retry_blocked: bool
    backoff_plan: str
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "max_requests_per_minute": self.max_requests_per_minute, "max_order_requests_per_minute": self.max_order_requests_per_minute, "cool_down_seconds": self.cool_down_seconds, "retry_blocked": self.retry_blocked, "backoff_plan": self.backoff_plan}

@dataclass(frozen=True)
class RateLimitSimulation:
    rules: tuple[RateLimitRule, ...]
    exceeded: bool
    action_taken: str
    no_real_sleep: bool
    def to_dict(self) -> dict:
        return {"rules": [r.to_dict() for r in self.rules], "exceeded": self.exceeded, "action_taken": self.action_taken, "no_real_sleep": self.no_real_sleep}

DEFAULT_RULES = (
    RateLimitRule("general", 1200, 10, 60.0, True, "exponential: 1s, 2s, 4s, 8s, 16s, 32s, 60s"),
    RateLimitRule("order", 10, 10, 60.0, True, "exponential: 1s, 2s, 4s, 8s, 16s, 32s, 60s"),
    RateLimitRule("cancel", 10, 10, 60.0, True, "exponential: 1s, 2s, 4s, 8s, 16s, 32s, 60s"),
)

def simulate_rate_limit(request_count: int, order_count: int) -> RateLimitSimulation:
    exceeded = request_count > 1200 or order_count > 10
    action = "BLOCKED: rate limit exceeded, retry blocked" if exceeded else "OK: within limits"
    return RateLimitSimulation(DEFAULT_RULES, exceeded, action, True)

def write_simulation(sim: RateLimitSimulation, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sim.to_dict(), indent=2), encoding="utf-8")
