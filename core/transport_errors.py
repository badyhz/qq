"""Transport error taxonomy — structured error classification.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    SERVER = "server"
    CLIENT = "client"
    GOVERNANCE = "governance"
    SCHEMA = "schema"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    TRANSIENT = "transient"   # retry-safe
    PERMANENT = "permanent"   # don't retry
    CRITICAL = "critical"     # halt


@dataclass
class TransportErrorInfo:
    category: ErrorCategory
    severity: ErrorSeverity
    status_code: int | None
    message: str
    retryable: bool
    context: Dict[str, str] = field(default_factory=dict)


# HTTP status -> error classification
_STATUS_MAP: Dict[int, TransportErrorInfo] = {
    400: TransportErrorInfo(ErrorCategory.CLIENT, ErrorSeverity.PERMANENT, 400, "bad request", False),
    401: TransportErrorInfo(ErrorCategory.AUTH, ErrorSeverity.PERMANENT, 401, "unauthorized", False),
    403: TransportErrorInfo(ErrorCategory.AUTH, ErrorSeverity.PERMANENT, 403, "forbidden", False),
    404: TransportErrorInfo(ErrorCategory.CLIENT, ErrorSeverity.PERMANENT, 404, "not found", False),
    408: TransportErrorInfo(ErrorCategory.TIMEOUT, ErrorSeverity.TRANSIENT, 408, "request timeout", True),
    429: TransportErrorInfo(ErrorCategory.RATE_LIMIT, ErrorSeverity.TRANSIENT, 429, "rate limited", True),
    500: TransportErrorInfo(ErrorCategory.SERVER, ErrorSeverity.TRANSIENT, 500, "internal server error", True),
    502: TransportErrorInfo(ErrorCategory.SERVER, ErrorSeverity.TRANSIENT, 502, "bad gateway", True),
    503: TransportErrorInfo(ErrorCategory.SERVER, ErrorSeverity.TRANSIENT, 503, "service unavailable", True),
    504: TransportErrorInfo(ErrorCategory.TIMEOUT, ErrorSeverity.TRANSIENT, 504, "gateway timeout", True),
}


def classify_error(
    status_code: int | None = None,
    exception: Exception | None = None,
    governance_blocked: bool = False,
) -> TransportErrorInfo:
    """Classify a transport error into structured taxonomy."""

    if governance_blocked:
        return TransportErrorInfo(
            ErrorCategory.GOVERNANCE, ErrorSeverity.CRITICAL,
            status_code, "governance policy blocked request", False,
        )

    if exception is not None:
        exc_name = type(exception).__name__
        if "timeout" in exc_name.lower() or "TimeoutError" in exc_name:
            return TransportErrorInfo(
                ErrorCategory.TIMEOUT, ErrorSeverity.TRANSIENT,
                None, f"timeout: {exception}", True,
            )
        if "connection" in exc_name.lower():
            return TransportErrorInfo(
                ErrorCategory.NETWORK, ErrorSeverity.TRANSIENT,
                None, f"connection error: {exception}", True,
            )
        return TransportErrorInfo(
            ErrorCategory.UNKNOWN, ErrorSeverity.PERMANENT,
            None, f"{exc_name}: {exception}", False,
        )

    if status_code is not None:
        if status_code in _STATUS_MAP:
            return _STATUS_MAP[status_code]
        if 400 <= status_code < 500:
            return TransportErrorInfo(
                ErrorCategory.CLIENT, ErrorSeverity.PERMANENT,
                status_code, f"client error {status_code}", False,
            )
        if 500 <= status_code < 600:
            return TransportErrorInfo(
                ErrorCategory.SERVER, ErrorSeverity.TRANSIENT,
                status_code, f"server error {status_code}", True,
            )

    return TransportErrorInfo(
        ErrorCategory.UNKNOWN, ErrorSeverity.PERMANENT,
        status_code, "unknown error", False,
    )
