"""Governance failure taxonomy — structured classification for workflow/runtime safety.

Pure simulation. No network calls. No file I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FailureCategory(Enum):
    POLICY_BLOCK = "policy_block"
    SANDBOX_BLOCK = "sandbox_block"
    ADAPTER_FAILURE = "adapter_failure"
    TRANSPORT_FAILURE = "transport_failure"
    VALIDATION_FAILURE = "validation_failure"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


class FailureSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class GovernanceFailure:
    category: FailureCategory
    severity: FailureSeverity
    code: str
    message: str
    source: str = ""
    retryable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── classification maps ──────────────────────────────────────────────

_STATUS_CATEGORY: Dict[int, FailureCategory] = {
    403: FailureCategory.SANDBOX_BLOCK,
    429: FailureCategory.RATE_LIMIT,
    408: FailureCategory.TIMEOUT,
    504: FailureCategory.TIMEOUT,
}

_STATUS_SEVERITY: Dict[int, FailureSeverity] = {
    429: FailureSeverity.WARNING,
    403: FailureSeverity.ERROR,
    408: FailureSeverity.WARNING,
    500: FailureSeverity.ERROR,
    502: FailureSeverity.ERROR,
    503: FailureSeverity.ERROR,
    504: FailureSeverity.WARNING,
}

_RETRYABLE_CATEGORIES = {FailureCategory.RATE_LIMIT, FailureCategory.TIMEOUT}
_RETRYABLE_STATUSES = {429, 408, 502, 503, 504}

_KEYWORD_CATEGORY: Dict[str, FailureCategory] = {
    "policy": FailureCategory.POLICY_BLOCK,
    "forbidden": FailureCategory.POLICY_BLOCK,
    "blocked": FailureCategory.POLICY_BLOCK,
    "sandbox": FailureCategory.SANDBOX_BLOCK,
    "adapter": FailureCategory.ADAPTER_FAILURE,
    "transport": FailureCategory.TRANSPORT_FAILURE,
    "validation": FailureCategory.VALIDATION_FAILURE,
    "invalid": FailureCategory.VALIDATION_FAILURE,
    "timeout": FailureCategory.TIMEOUT,
    "rate_limit": FailureCategory.RATE_LIMIT,
    "rate limited": FailureCategory.RATE_LIMIT,
}


# ── pure functions ───────────────────────────────────────────────────


def classify_governance_failure(
    *,
    status_code: int | None = None,
    message: str = "",
    source: str = "",
    category: FailureCategory | None = None,
    severity: FailureSeverity | None = None,
    retryable: bool | None = None,
    metadata: Dict[str, Any] | None = None,
) -> GovernanceFailure:
    """Classify a governance failure from available signals.

    All inputs are optional. Unknown/unprovided signals get safe defaults.
    Deterministic. No I/O.
    """
    # category resolution: explicit > status_code > keyword > UNKNOWN
    if category is None:
        if status_code is not None and status_code in _STATUS_CATEGORY:
            category = _STATUS_CATEGORY[status_code]
        else:
            category = _classify_from_message(message)

    # severity resolution: explicit > status_code > category default
    if severity is None:
        if status_code is not None and status_code in _STATUS_SEVERITY:
            severity = _STATUS_SEVERITY[status_code]
        else:
            severity = _category_default_severity(category)

    # retryable resolution: explicit > category > status_code
    if retryable is None:
        if category in _RETRYABLE_CATEGORIES:
            retryable = True
        elif status_code is not None:
            retryable = status_code in _RETRYABLE_STATUSES
        else:
            retryable = False

    code = _build_code(category, status_code)

    return GovernanceFailure(
        category=category,
        severity=severity,
        code=code,
        message=message,
        source=source,
        retryable=retryable,
        metadata=dict(metadata) if metadata else {},
    )


def failure_to_dict(failure: GovernanceFailure) -> Dict[str, Any]:
    """Serialize GovernanceFailure to a plain dict. No I/O."""
    return {
        "category": failure.category.value,
        "severity": failure.severity.value,
        "code": failure.code,
        "message": failure.message,
        "source": failure.source,
        "retryable": failure.retryable,
        "metadata": dict(failure.metadata),
    }


def summarize_failures(failures: List[GovernanceFailure]) -> Dict[str, Any]:
    """Aggregate counts by category and severity. No I/O."""
    by_category: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    retryable_count = 0

    for f in failures:
        cat = f.category.value
        sev = f.severity.value
        by_category[cat] = by_category.get(cat, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1
        if f.retryable:
            retryable_count += 1

    return {
        "total": len(failures),
        "by_category": by_category,
        "by_severity": by_severity,
        "retryable": retryable_count,
        "non_retryable": len(failures) - retryable_count,
    }


# ── internal helpers ─────────────────────────────────────────────────


def _classify_from_message(message: str) -> FailureCategory:
    lower = message.lower()
    for keyword, cat in _KEYWORD_CATEGORY.items():
        if keyword in lower:
            return cat
    return FailureCategory.UNKNOWN


def _category_default_severity(category: FailureCategory) -> FailureSeverity:
    return {
        FailureCategory.POLICY_BLOCK: FailureSeverity.CRITICAL,
        FailureCategory.SANDBOX_BLOCK: FailureSeverity.ERROR,
        FailureCategory.ADAPTER_FAILURE: FailureSeverity.ERROR,
        FailureCategory.TRANSPORT_FAILURE: FailureSeverity.WARNING,
        FailureCategory.VALIDATION_FAILURE: FailureSeverity.ERROR,
        FailureCategory.TIMEOUT: FailureSeverity.WARNING,
        FailureCategory.RATE_LIMIT: FailureSeverity.WARNING,
        FailureCategory.UNKNOWN: FailureSeverity.ERROR,
    }.get(category, FailureSeverity.ERROR)


def _build_code(category: FailureCategory, status_code: int | None) -> str:
    prefix = category.value.upper()
    if status_code is not None:
        return f"{prefix}_{status_code}"
    return prefix
