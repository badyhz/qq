from __future__ import annotations

import time
from enum import Enum
from dataclasses import dataclass, field


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: float = 0.0
        self._half_open_attempts: int = 0
        self._history: list[dict] = []

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    @property
    def state(self) -> CircuitState:
        self._check_recovery()
        return self._state

    def record_success(self) -> CircuitState:
        self._success_count += 1
        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.CLOSED, "success in half_open")
        else:
            self._failure_count = 0
        return self.state

    def record_failure(self, reason: str = "") -> CircuitState:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN, reason or "failure in half_open")
        elif self._failure_count >= self.failure_threshold:
            self._transition(CircuitState.OPEN, reason or "threshold reached")
        return self.state

    def trip(self, reason: str = "") -> None:
        self._transition(CircuitState.OPEN, reason or "force trip")

    def reset(self) -> None:
        self._transition(CircuitState.CLOSED, "force reset")

    def allow_request(self) -> bool:
        s = self.state
        if s == CircuitState.OPEN:
            return False
        if s == CircuitState.HALF_OPEN:
            if self._half_open_attempts < self.half_open_max:
                self._half_open_attempts += 1
                return True
            return False
        return True

    def _check_recovery(self) -> None:
        if self._state == CircuitState.OPEN:
            now = time.monotonic()
            if now - self._last_failure_time >= self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN, "recovery timeout elapsed")

    def _transition(self, new_state: CircuitState, reason: str) -> None:
        old = self._state
        if old == new_state:
            return
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_attempts = 0
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._half_open_attempts = 0
        if new_state == CircuitState.OPEN:
            self._last_failure_time = time.monotonic()
        self._state = new_state
        self._history.append({
            "from": old.value,
            "to": new_state.value,
            "reason": reason,
            "ts": time.time(),
        })

    def summary(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "half_open_attempts": self._half_open_attempts,
            "history_len": len(self._history),
        }
