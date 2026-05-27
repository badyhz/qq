"""Governance failure deterministic examples factory.

Pure data construction for tests, docs, CLI demos.
No timestamps. No random. No environment. No file I/O. No network.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.governance_failure_taxonomy import (
    FailureCategory,
    FailureSeverity,
    GovernanceFailure,
)
from core.governance_failure_report import (
    GovernanceFailureReport,
    build_governance_failure_report,
    report_to_dict,
)
from core.governance_failure_regression_packet import (
    GovernanceFailureRegressionPacket,
    build_governance_failure_regression_packet,
    packet_to_dict,
)

# ── canonical example failures ───────────────────────────────────────

_PASS_FAILURES: List[GovernanceFailure] = []

_WARN_FAILURES: List[GovernanceFailure] = [
    GovernanceFailure(
        category=FailureCategory.RATE_LIMIT,
        severity=FailureSeverity.WARNING,
        code="RATE_LIMIT_429",
        message="Rate limit exceeded, retryable",
        source="exchange_adapter",
        retryable=True,
        metadata={"retry_after": 2},
    ),
    GovernanceFailure(
        category=FailureCategory.TIMEOUT,
        severity=FailureSeverity.WARNING,
        code="TIMEOUT_408",
        message="Request timeout, retryable",
        source="transport_layer",
        retryable=True,
        metadata={"timeout_ms": 5000},
    ),
]

_FAIL_FAILURES: List[GovernanceFailure] = [
    GovernanceFailure(
        category=FailureCategory.ADAPTER_FAILURE,
        severity=FailureSeverity.ERROR,
        code="ADAPTER_FAILURE",
        message="Adapter returned invalid response",
        source="binance_adapter",
        retryable=False,
        metadata={"raw_response": "malformed"},
    ),
]

_BLOCKED_FAILURES: List[GovernanceFailure] = [
    GovernanceFailure(
        category=FailureCategory.POLICY_BLOCK,
        severity=FailureSeverity.CRITICAL,
        code="POLICY_BLOCK",
        message="Policy violation: blocked by governance rule",
        source="policy_engine",
        retryable=False,
        metadata={"rule_id": "GOV-001"},
    ),
]

_MIXED_FAILURES: List[GovernanceFailure] = [
    GovernanceFailure(
        category=FailureCategory.RATE_LIMIT,
        severity=FailureSeverity.WARNING,
        code="RATE_LIMIT_429",
        message="Rate limit exceeded, retryable",
        source="exchange_adapter",
        retryable=True,
        metadata={"retry_after": 2},
    ),
    GovernanceFailure(
        category=FailureCategory.ADAPTER_FAILURE,
        severity=FailureSeverity.ERROR,
        code="ADAPTER_FAILURE",
        message="Adapter returned invalid response",
        source="binance_adapter",
        retryable=False,
        metadata={"raw_response": "malformed"},
    ),
    GovernanceFailure(
        category=FailureCategory.POLICY_BLOCK,
        severity=FailureSeverity.CRITICAL,
        code="POLICY_BLOCK",
        message="Policy violation: blocked by governance rule",
        source="policy_engine",
        retryable=False,
        metadata={"rule_id": "GOV-001"},
    ),
]

# ── kind → failures map ─────────────────────────────────────────────

_FAILURES_BY_KIND: Dict[str, List[GovernanceFailure]] = {
    "pass": _PASS_FAILURES,
    "warn": _WARN_FAILURES,
    "fail": _FAIL_FAILURES,
    "blocked": _BLOCKED_FAILURES,
    "mixed": _MIXED_FAILURES,
}

_VALID_KINDS = frozenset(_FAILURES_BY_KIND.keys())


# ── builders ─────────────────────────────────────────────────────────


def build_pass_example_failures() -> List[GovernanceFailure]:
    """Return empty failure list (PASS scenario)."""
    return list(_PASS_FAILURES)


def build_warn_example_failures() -> List[GovernanceFailure]:
    """Return warning-level retryable failures (WARN scenario)."""
    return list(_WARN_FAILURES)


def build_fail_example_failures() -> List[GovernanceFailure]:
    """Return error-level failure (FAIL scenario)."""
    return list(_FAIL_FAILURES)


def build_blocked_example_failures() -> List[GovernanceFailure]:
    """Return critical non-retryable failure (BLOCKED scenario)."""
    return list(_BLOCKED_FAILURES)


def build_mixed_example_failures() -> List[GovernanceFailure]:
    """Return mixed severity failures (BLOCKED scenario due to critical)."""
    return list(_MIXED_FAILURES)


def build_example_report(kind: str) -> Dict[str, Any]:
    """Build a deterministic report dict for the given kind.

    Raises ValueError for unsupported kinds.
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"Unsupported kind: {kind!r}. Valid: {sorted(_VALID_KINDS)}"
        )
    failures = _FAILURES_BY_KIND[kind]
    report = build_governance_failure_report(
        failures,
        title=f"Example {kind.upper()} Report",
    )
    return report_to_dict(report)


def build_example_packet(kind: str) -> Dict[str, Any]:
    """Build a deterministic regression packet dict for the given kind.

    Raises ValueError for unsupported kinds.
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"Unsupported kind: {kind!r}. Valid: {sorted(_VALID_KINDS)}"
        )
    failures = _FAILURES_BY_KIND[kind]
    packet = build_governance_failure_regression_packet(
        failures,
        title=f"Example {kind.upper()} Packet",
    )
    return packet_to_dict(packet)
