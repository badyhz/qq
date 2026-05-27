"""T782 — Transport error taxonomy tests."""

import pytest
from core.transport_errors import classify_error, ErrorCategory, ErrorSeverity


def test_classify_429():
    info = classify_error(status_code=429)
    assert info.category == ErrorCategory.RATE_LIMIT
    assert info.severity == ErrorSeverity.TRANSIENT
    assert info.retryable is True


def test_classify_401():
    info = classify_error(status_code=401)
    assert info.category == ErrorCategory.AUTH
    assert info.retryable is False


def test_classify_500():
    info = classify_error(status_code=500)
    assert info.category == ErrorCategory.SERVER
    assert info.retryable is True


def test_classify_400():
    info = classify_error(status_code=400)
    assert info.category == ErrorCategory.CLIENT
    assert info.retryable is False


def test_classify_timeout_exception():
    info = classify_error(exception=TimeoutError("timed out"))
    assert info.category == ErrorCategory.TIMEOUT
    assert info.retryable is True


def test_classify_connection_exception():
    info = classify_error(exception=ConnectionError("refused"))
    assert info.category == ErrorCategory.NETWORK
    assert info.retryable is True


def test_classify_governance_blocked():
    info = classify_error(status_code=403, governance_blocked=True)
    assert info.category == ErrorCategory.GOVERNANCE
    assert info.severity == ErrorSeverity.CRITICAL
    assert info.retryable is False


def test_classify_unknown_status():
    info = classify_error(status_code=418)
    assert info.category == ErrorCategory.CLIENT
    assert info.retryable is False


def test_classify_server_502():
    info = classify_error(status_code=502)
    assert info.category == ErrorCategory.SERVER
    assert info.retryable is True


def test_classify_unknown_exception():
    info = classify_error(exception=ValueError("bad value"))
    assert info.category == ErrorCategory.UNKNOWN
    assert info.retryable is False


def test_classify_no_input():
    info = classify_error()
    assert info.category == ErrorCategory.UNKNOWN
    assert info.retryable is False
