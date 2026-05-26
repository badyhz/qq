"""Formalized API response types and normalization layer."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    AUTH_FAILURE = "auth_failure"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class NormalizedResponse:
    status: ResponseStatus
    status_code: int
    data: dict | None = None
    error_message: str | None = None
    retryable: bool = False
    rate_limit_reset_seconds: float | None = None
    request_id: str | None = None
    model: str | None = None
    tokens_used: int | None = None


def classify_error(status_code: int, body: dict | None = None) -> ResponseStatus:
    """Classify HTTP status code to ResponseStatus."""
    if 200 <= status_code <= 299:
        return ResponseStatus.SUCCESS
    if status_code in (401, 403):
        return ResponseStatus.AUTH_FAILURE
    if status_code == 429:
        return ResponseStatus.RATE_LIMITED
    if status_code in (408, 504):
        return ResponseStatus.TIMEOUT
    if 400 <= status_code <= 499:
        return ResponseStatus.ERROR
    if 500 <= status_code <= 599:
        return ResponseStatus.ERROR
    return ResponseStatus.UNKNOWN


def is_retryable(status: ResponseStatus) -> bool:
    """Check if response indicates retryable error."""
    return status in (ResponseStatus.RATE_LIMITED, ResponseStatus.TIMEOUT, ResponseStatus.ERROR)


def extract_rate_limit_info(headers: dict) -> dict:
    """Extract rate limit info from response headers."""
    result: dict = {}
    remaining = headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        try:
            result["remaining"] = int(remaining)
        except (ValueError, TypeError):
            pass

    reset = headers.get("X-RateLimit-Reset")
    if reset is not None:
        try:
            reset_ts = float(reset)
            delta = reset_ts - time.time()
            result["reset_seconds"] = max(delta, 0.0)
        except (ValueError, TypeError):
            pass

    retry_after = headers.get("Retry-After")
    if retry_after is not None:
        try:
            result["retry_after"] = float(retry_after)
        except (ValueError, TypeError):
            pass

    return result


def normalize_response(raw_response: dict, status_code: int = 200) -> NormalizedResponse:
    """Normalize any API response to standard format."""
    status = classify_error(status_code, raw_response)

    error_msg = None
    if status != ResponseStatus.SUCCESS:
        error_msg = raw_response.get("error", {}).get("message") or raw_response.get("message") or raw_response.get("error")
        if isinstance(error_msg, dict):
            error_msg = error_msg.get("message", str(error_msg))

    data = raw_response if status == ResponseStatus.SUCCESS else raw_response.get("data")

    rate_limit_reset = None
    rl_info = extract_rate_limit_info(raw_response.get("_headers", {}))
    if "retry_after" in rl_info:
        rate_limit_reset = rl_info["retry_after"]
    elif "reset_seconds" in rl_info:
        rate_limit_reset = rl_info["reset_seconds"]

    request_id = raw_response.get("request_id") or raw_response.get("id")
    model = raw_response.get("model")
    tokens_used = None
    usage = raw_response.get("usage")
    if isinstance(usage, dict):
        tokens_used = usage.get("total_tokens") or usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

    return NormalizedResponse(
        status=status,
        status_code=status_code,
        data=data,
        error_message=error_msg,
        retryable=is_retryable(status),
        rate_limit_reset_seconds=rate_limit_reset,
        request_id=str(request_id) if request_id is not None else None,
        model=model,
        tokens_used=tokens_used,
    )


def format_error_response(
    status: ResponseStatus,
    message: str,
    status_code: int = 0,
) -> NormalizedResponse:
    """Create error response."""
    return NormalizedResponse(
        status=status,
        status_code=status_code,
        error_message=message,
        retryable=is_retryable(status),
    )
