from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FailureType(Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    SAFETY_VIOLATION = "safety_violation"
    BUDGET_EXCEEDED = "budget_exceeded"
    UNKNOWN = "unknown"


class RetryPolicy:
    def __init__(self, max_attempts: int = 3, timeout_seconds: float = 30.0,
                 base_backoff: float = 1.0, max_backoff: float = 60.0,
                 retryable_failures: set[FailureType] | None = None):
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.retryable_failures = retryable_failures or {
            FailureType.TIMEOUT, FailureType.RATE_LIMIT, FailureType.API_ERROR
        }

    def should_retry(self, failure_type: FailureType, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            return False
        return failure_type in self.retryable_failures

    def backoff_seconds(self, attempt: int) -> float:
        delay = self.base_backoff * (2 ** attempt)
        return min(delay, self.max_backoff)

    def classify_failure(self, error_message: str) -> FailureType:
        msg = error_message.lower()
        if "timeout" in msg:
            return FailureType.TIMEOUT
        if "rate limit" in msg or "429" in msg:
            return FailureType.RATE_LIMIT
        if "safety" in msg or "violation" in msg:
            return FailureType.SAFETY_VIOLATION
        if "budget" in msg or "exceeded" in msg:
            return FailureType.BUDGET_EXCEEDED
        if "api" in msg or "500" in msg or "502" in msg or "503" in msg:
            return FailureType.API_ERROR
        return FailureType.UNKNOWN

    def next_attempt_delay(self, failure_type: FailureType, attempt: int) -> float | None:
        if not self.should_retry(failure_type, attempt):
            return None
        return self.backoff_seconds(attempt)

    def summary(self) -> dict:
        return {
            "max_attempts": self.max_attempts,
            "timeout_seconds": self.timeout_seconds,
            "base_backoff": self.base_backoff,
            "max_backoff": self.max_backoff,
            "retryable_failures": [f.value for f in self.retryable_failures],
        }


@dataclass
class TaskRetryState:
    task_id: str
    attempt: int = 0
    last_failure: FailureType | None = None
    total_delay: float = 0.0

    def record_failure(self, failure_type: FailureType, policy: RetryPolicy) -> dict:
        self.attempt += 1
        self.last_failure = failure_type
        delay = policy.next_attempt_delay(failure_type, self.attempt - 1)
        if delay is not None:
            self.total_delay += delay
        return {
            "attempt": self.attempt,
            "failure_type": failure_type.value,
            "delay": delay,
            "can_retry": self.can_retry(policy),
            "is_final": self.is_final_failure(policy),
            "total_delay": self.total_delay,
        }

    def can_retry(self, policy: RetryPolicy) -> bool:
        if self.last_failure is None:
            return True
        return policy.should_retry(self.last_failure, self.attempt)

    def is_final_failure(self, policy: RetryPolicy) -> bool:
        return not self.can_retry(policy)
