from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from core.workflow_circuit_breaker import CircuitBreaker, CircuitState


def test_starts_closed():
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request()


def test_stays_closed_under_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure("e1")
    cb.record_failure("e2")
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request()


def test_trips_at_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure("e1")
    cb.record_failure("e2")
    assert cb.state == CircuitState.CLOSED
    cb.record_failure("e3")
    assert cb.state == CircuitState.OPEN
    assert not cb.allow_request()


def test_open_blocks_requests():
    cb = CircuitBreaker(failure_threshold=2)
    cb.record_failure("e1")
    cb.record_failure("e2")
    assert cb.state == CircuitState.OPEN
    assert not cb.allow_request()
    assert not cb.allow_request()


def test_half_open_after_recovery_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure("e1")
    cb.record_failure("e2")
    assert cb.state == CircuitState.OPEN
    time.sleep(0.15)
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.allow_request()


def test_half_open_success_closes():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
    cb.record_failure("e1")
    cb.record_failure("e2")
    time.sleep(0.1)
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_half_open_failure_reopens():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
    cb.record_failure("e1")
    cb.record_failure("e2")
    time.sleep(0.1)
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_failure("still broken")
    assert cb.state == CircuitState.OPEN


def test_force_trip():
    cb = CircuitBreaker(failure_threshold=10)
    assert cb.state == CircuitState.CLOSED
    cb.trip("manual")
    assert cb.state == CircuitState.OPEN
    assert not cb.allow_request()


def test_force_reset():
    cb = CircuitBreaker(failure_threshold=1)
    cb.record_failure("e1")
    assert cb.state == CircuitState.OPEN
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request()


def test_summary_stats():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
    cb.record_failure("e1")
    cb.record_failure("e2")
    s = cb.summary()
    assert s["state"] == "closed"
    assert s["failure_count"] == 2
    assert s["success_count"] == 0
    assert s["failure_threshold"] == 3
    assert s["recovery_timeout"] == 10.0
    assert s["half_open_attempts"] == 0
    assert s["history_len"] == 0


def test_history_tracking():
    cb = CircuitBreaker(failure_threshold=2)
    cb.record_failure("e1")
    cb.record_failure("e2")
    assert len(cb.history) == 1
    assert cb.history[0]["from"] == "closed"
    assert cb.history[0]["to"] == "open"

    cb.reset()
    assert len(cb.history) == 2
    assert cb.history[1]["from"] == "open"
    assert cb.history[1]["to"] == "closed"


def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure("e1")
    cb.record_failure("e2")
    assert cb._failure_count == 2
    cb.record_success()
    assert cb._failure_count == 0
    cb.record_failure("e1")
    assert cb._failure_count == 1
    assert cb.state == CircuitState.CLOSED
