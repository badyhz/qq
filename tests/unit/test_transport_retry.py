"""T771 — Retry transport wrapper tests."""

import asyncio
import pytest

from core.http_transport import TransportResponse, HTTPTransport
from core.transport_retry import RetryTransport, RetryConfig, BackoffStrategy


class FlakyTransport(HTTPTransport):
    def __init__(self, fail_count=0, fail_status=500):
        self._fail_count = fail_count
        self._fail_status = fail_status
        self._call_count = 0

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self._call_count += 1
        if self._call_count <= self._fail_count:
            return TransportResponse(
                status_code=self._fail_status, headers={},
                body={"error": "transient"}, duration_ms=0.0, success=False,
            )
        return TransportResponse(
            status_code=200, headers={}, body={"status": "ok"},
            duration_ms=0.0, success=True,
        )


class ErrorTransport(HTTPTransport):
    def __init__(self, fail_count=0):
        self._fail_count = fail_count
        self._call_count = 0

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self._call_count += 1
        if self._call_count <= self._fail_count:
            raise ConnectionError(f"connection refused #{self._call_count}")
        return TransportResponse(
            status_code=200, headers={}, body={"ok": True},
            duration_ms=0.0, success=True,
        )


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_retry_succeeds_after_transient_failures():
    async def go():
        flaky = FlakyTransport(fail_count=2, fail_status=503)
        cfg = RetryConfig(max_retries=3, base_delay_seconds=0.01, backoff=BackoffStrategy.FIXED)
        t = RetryTransport(flaky, cfg)
        r = await t.request("GET", "https://example.com")
        assert r.status_code == 200
        assert flaky._call_count == 3
        assert len(t.attempt_log()) == 3
    _run(go())


def test_retry_exhausted_returns_last_response():
    async def go():
        flaky = FlakyTransport(fail_count=5, fail_status=503)
        cfg = RetryConfig(max_retries=2, base_delay_seconds=0.01, backoff=BackoffStrategy.FIXED)
        t = RetryTransport(flaky, cfg)
        r = await t.request("GET", "https://example.com")
        assert r.status_code == 503
        assert flaky._call_count == 3
    _run(go())


def test_no_retry_on_success():
    async def go():
        cfg = RetryConfig(max_retries=3, base_delay_seconds=0.01)
        t = RetryTransport(FlakyTransport(fail_count=0), cfg)
        r = await t.request("GET", "https://example.com")
        assert r.status_code == 200
        assert len(t.attempt_log()) == 1
    _run(go())


def test_no_retry_on_non_retryable_status():
    async def go():
        flaky = FlakyTransport(fail_count=1, fail_status=400)
        cfg = RetryConfig(max_retries=3, base_delay_seconds=0.01)
        t = RetryTransport(flaky, cfg)
        r = await t.request("GET", "https://example.com")
        assert r.status_code == 400
        assert flaky._call_count == 1
    _run(go())


def test_retry_on_429():
    async def go():
        flaky = FlakyTransport(fail_count=1, fail_status=429)
        cfg = RetryConfig(max_retries=3, base_delay_seconds=0.01, backoff=BackoffStrategy.FIXED)
        t = RetryTransport(flaky, cfg)
        r = await t.request("GET", "https://example.com")
        assert r.status_code == 200
        assert flaky._call_count == 2
    _run(go())


def test_retry_on_exception():
    async def go():
        err = ErrorTransport(fail_count=2)
        cfg = RetryConfig(max_retries=3, base_delay_seconds=0.01, backoff=BackoffStrategy.FIXED)
        t = RetryTransport(err, cfg)
        r = await t.request("GET", "https://example.com")
        assert r.status_code == 200
        assert err._call_count == 3
    _run(go())


def test_retry_exception_exhausted_raises():
    async def go():
        err = ErrorTransport(fail_count=5)
        cfg = RetryConfig(max_retries=2, base_delay_seconds=0.01, backoff=BackoffStrategy.FIXED)
        t = RetryTransport(err, cfg)
        with pytest.raises(ConnectionError):
            await t.request("GET", "https://example.com")
    _run(go())


def test_backoff_strategy_linear():
    cfg = RetryConfig(max_retries=3, base_delay_seconds=1.0, backoff=BackoffStrategy.LINEAR)
    t = RetryTransport(FlakyTransport(fail_count=0), cfg)
    assert t._compute_delay(0) == 1.0
    assert t._compute_delay(1) == 2.0
    assert t._compute_delay(2) == 3.0


def test_backoff_strategy_exponential():
    cfg = RetryConfig(max_retries=5, base_delay_seconds=1.0, backoff=BackoffStrategy.EXPONENTIAL)
    t = RetryTransport(FlakyTransport(fail_count=0), cfg)
    assert t._compute_delay(0) == 1.0
    assert t._compute_delay(1) == 2.0
    assert t._compute_delay(2) == 4.0
    assert t._compute_delay(3) == 8.0


def test_backoff_max_delay_cap():
    cfg = RetryConfig(max_retries=10, base_delay_seconds=1.0, max_delay_seconds=5.0, backoff=BackoffStrategy.EXPONENTIAL)
    t = RetryTransport(FlakyTransport(fail_count=0), cfg)
    assert t._compute_delay(5) == 5.0
    assert t._compute_delay(10) == 5.0


def test_attempt_log_records_all_attempts():
    async def go():
        flaky = FlakyTransport(fail_count=2, fail_status=502)
        cfg = RetryConfig(max_retries=3, base_delay_seconds=0.01, backoff=BackoffStrategy.FIXED)
        t = RetryTransport(flaky, cfg)
        await t.request("POST", "https://api.test.com/data")
        log = t.attempt_log()
        assert len(log) == 3
        assert log[0].status_code == 502
        assert log[2].status_code == 200
    _run(go())
