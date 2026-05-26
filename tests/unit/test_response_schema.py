"""Unit tests for core.response_schema."""

import pytest

from core.response_schema import (
    NormalizedResponse,
    ResponseStatus,
    classify_error,
    extract_rate_limit_info,
    format_error_response,
    is_retryable,
    normalize_response,
)


class TestNormalizeResponse:
    def test_success_body(self):
        raw = {"result": "ok", "data": {"price": 100}}
        resp = normalize_response(raw, 200)
        assert resp.status == ResponseStatus.SUCCESS
        assert resp.status_code == 200
        assert resp.data == raw
        assert resp.error_message is None
        assert resp.retryable is False

    def test_error_body(self):
        raw = {"error": {"message": "bad request"}}
        resp = normalize_response(raw, 400)
        assert resp.status == ResponseStatus.ERROR
        assert resp.status_code == 400
        assert resp.error_message == "bad request"
        assert resp.retryable is True

    def test_success_with_usage(self):
        raw = {"model": "gpt-4", "usage": {"total_tokens": 150}}
        resp = normalize_response(raw, 200)
        assert resp.model == "gpt-4"
        assert resp.tokens_used == 150

    def test_success_with_request_id(self):
        raw = {"id": "req-123", "data": {}}
        resp = normalize_response(raw, 200)
        assert resp.request_id == "req-123"


class TestClassifyError:
    def test_200_is_success(self):
        assert classify_error(200) == ResponseStatus.SUCCESS

    def test_201_is_success(self):
        assert classify_error(201) == ResponseStatus.SUCCESS

    def test_299_is_success(self):
        assert classify_error(299) == ResponseStatus.SUCCESS

    def test_401_is_auth_failure(self):
        assert classify_error(401) == ResponseStatus.AUTH_FAILURE

    def test_403_is_auth_failure(self):
        assert classify_error(403) == ResponseStatus.AUTH_FAILURE

    def test_429_is_rate_limited(self):
        assert classify_error(429) == ResponseStatus.RATE_LIMITED

    def test_408_is_timeout(self):
        assert classify_error(408) == ResponseStatus.TIMEOUT

    def test_504_is_timeout(self):
        assert classify_error(504) == ResponseStatus.TIMEOUT

    def test_400_is_error(self):
        assert classify_error(400) == ResponseStatus.ERROR

    def test_404_is_error(self):
        assert classify_error(404) == ResponseStatus.ERROR

    def test_499_is_error(self):
        assert classify_error(499) == ResponseStatus.ERROR

    def test_500_is_error(self):
        assert classify_error(500) == ResponseStatus.ERROR

    def test_503_is_error(self):
        assert classify_error(503) == ResponseStatus.ERROR

    def test_599_is_error(self):
        assert classify_error(599) == ResponseStatus.ERROR

    def test_100_is_unknown(self):
        assert classify_error(100) == ResponseStatus.UNKNOWN

    def test_0_is_unknown(self):
        assert classify_error(0) == ResponseStatus.UNKNOWN

    def test_999_is_unknown(self):
        assert classify_error(999) == ResponseStatus.UNKNOWN


class TestIsRetryable:
    def test_rate_limited_retryable(self):
        assert is_retryable(ResponseStatus.RATE_LIMITED) is True

    def test_timeout_retryable(self):
        assert is_retryable(ResponseStatus.TIMEOUT) is True

    def test_error_retryable(self):
        assert is_retryable(ResponseStatus.ERROR) is True

    def test_success_not_retryable(self):
        assert is_retryable(ResponseStatus.SUCCESS) is False

    def test_auth_failure_not_retryable(self):
        assert is_retryable(ResponseStatus.AUTH_FAILURE) is False

    def test_unknown_not_retryable(self):
        assert is_retryable(ResponseStatus.UNKNOWN) is False


class TestExtractRateLimitInfo:
    def test_remaining(self):
        headers = {"X-RateLimit-Remaining": "42"}
        info = extract_rate_limit_info(headers)
        assert info["remaining"] == 42

    def test_reset(self):
        import time

        now = time.time()
        headers = {"X-RateLimit-Reset": str(now + 60)}
        info = extract_rate_limit_info(headers)
        assert 55 <= info["reset_seconds"] <= 65

    def test_retry_after(self):
        headers = {"Retry-After": "30"}
        info = extract_rate_limit_info(headers)
        assert info["retry_after"] == 30.0

    def test_empty_headers(self):
        info = extract_rate_limit_info({})
        assert info == {}

    def test_invalid_remaining(self):
        headers = {"X-RateLimit-Remaining": "abc"}
        info = extract_rate_limit_info(headers)
        assert "remaining" not in info


class TestFormatErrorResponse:
    def test_basic_error(self):
        resp = format_error_response(ResponseStatus.ERROR, "bad input", 400)
        assert resp.status == ResponseStatus.ERROR
        assert resp.status_code == 400
        assert resp.error_message == "bad input"
        assert resp.retryable is True

    def test_auth_error(self):
        resp = format_error_response(ResponseStatus.AUTH_FAILURE, "unauthorized")
        assert resp.status == ResponseStatus.AUTH_FAILURE
        assert resp.retryable is False
        assert resp.status_code == 0

    def test_rate_limit_error(self):
        resp = format_error_response(ResponseStatus.RATE_LIMITED, "slow down", 429)
        assert resp.retryable is True


class TestMultipleResponseTypes:
    def test_mixed_sequence(self):
        responses = [
            (normalize_response({"ok": True}, 200), ResponseStatus.SUCCESS, False),
            (normalize_response({"error": {"message": "no"}}, 401), ResponseStatus.AUTH_FAILURE, False),
            (normalize_response({"error": {"message": "slow"}}, 429), ResponseStatus.RATE_LIMITED, True),
            (normalize_response({"error": {"message": "timeout"}}, 504), ResponseStatus.TIMEOUT, True),
            (normalize_response({"error": {"message": "crash"}}, 500), ResponseStatus.ERROR, True),
        ]
        for resp, expected_status, expected_retryable in responses:
            assert resp.status == expected_status
            assert resp.retryable == expected_retryable
