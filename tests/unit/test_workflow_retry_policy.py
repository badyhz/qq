import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.workflow_retry_policy import (
    FailureType,
    RetryPolicy,
    TaskRetryState,
)


def test_policy_defaults():
    p = RetryPolicy()
    assert p.max_attempts == 3
    assert p.timeout_seconds == 30.0
    assert p.base_backoff == 1.0
    assert p.max_backoff == 60.0
    assert FailureType.TIMEOUT in p.retryable_failures
    assert FailureType.RATE_LIMIT in p.retryable_failures
    assert FailureType.API_ERROR in p.retryable_failures


def test_should_retry_timeout():
    p = RetryPolicy(max_attempts=3)
    assert p.should_retry(FailureType.TIMEOUT, 0) is True
    assert p.should_retry(FailureType.TIMEOUT, 1) is True
    assert p.should_retry(FailureType.TIMEOUT, 2) is True
    assert p.should_retry(FailureType.TIMEOUT, 3) is False


def test_should_retry_safety_violation_rejected():
    p = RetryPolicy()
    assert p.should_retry(FailureType.SAFETY_VIOLATION, 0) is False


def test_backoff_exponential():
    p = RetryPolicy(base_backoff=1.0)
    assert p.backoff_seconds(0) == 1.0
    assert p.backoff_seconds(1) == 2.0
    assert p.backoff_seconds(2) == 4.0


def test_backoff_capped():
    p = RetryPolicy(base_backoff=10.0, max_backoff=30.0)
    assert p.backoff_seconds(0) == 10.0
    assert p.backoff_seconds(1) == 20.0
    assert p.backoff_seconds(2) == 30.0
    assert p.backoff_seconds(3) == 30.0


def test_classify_timeout_error():
    p = RetryPolicy()
    assert p.classify_failure("request timeout after 30s") == FailureType.TIMEOUT


def test_classify_rate_limit_error():
    p = RetryPolicy()
    assert p.classify_failure("rate limit exceeded 429") == FailureType.RATE_LIMIT


def test_classify_unknown_error():
    p = RetryPolicy()
    assert p.classify_failure("something weird happened") == FailureType.UNKNOWN


def test_task_retry_state_lifecycle():
    p = RetryPolicy(max_attempts=3)
    s = TaskRetryState(task_id="t1")

    r = s.record_failure(FailureType.TIMEOUT, p)
    assert r["attempt"] == 1
    assert r["delay"] == 1.0
    assert r["can_retry"] is True
    assert r["is_final"] is False

    r = s.record_failure(FailureType.TIMEOUT, p)
    assert r["attempt"] == 2
    assert r["delay"] == 2.0
    assert r["can_retry"] is True

    r = s.record_failure(FailureType.TIMEOUT, p)
    assert r["attempt"] == 3
    assert r["can_retry"] is False
    assert r["is_final"] is True
    assert s.total_delay == 1.0 + 2.0 + 4.0


def test_task_retry_exhausted():
    p = RetryPolicy(max_attempts=2)
    s = TaskRetryState(task_id="t2")

    s.record_failure(FailureType.API_ERROR, p)
    s.record_failure(FailureType.API_ERROR, p)
    assert s.can_retry(p) is False
    assert s.is_final_failure(p) is True


def test_next_attempt_delay_none_when_exhausted():
    p = RetryPolicy(max_attempts=2)
    assert p.next_attempt_delay(FailureType.TIMEOUT, 0) == 1.0
    assert p.next_attempt_delay(FailureType.TIMEOUT, 1) == 2.0
    assert p.next_attempt_delay(FailureType.TIMEOUT, 2) is None
    assert p.next_attempt_delay(FailureType.SAFETY_VIOLATION, 0) is None


def test_summary_stats():
    p = RetryPolicy(max_attempts=5, timeout_seconds=60.0)
    s = p.summary()
    assert s["max_attempts"] == 5
    assert s["timeout_seconds"] == 60.0
    assert "rate_limit" in s["retryable_failures"]
    assert "timeout" in s["retryable_failures"]
