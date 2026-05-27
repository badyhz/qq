"""Runtime governance reason codes — stable registry for governance outcomes.

Pure simulation. No network calls. No file I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.governance_failure_taxonomy import FailureCategory, FailureSeverity


@dataclass(frozen=True)
class RuntimeGovernanceReasonCode:
    code: str
    category: FailureCategory
    severity: FailureSeverity
    retryable: bool
    description: str


_REGISTRY: List[RuntimeGovernanceReasonCode] = [
    RuntimeGovernanceReasonCode(
        code="RG_OK",
        category=FailureCategory.VALIDATION_FAILURE,
        severity=FailureSeverity.INFO,
        retryable=False,
        description="governance check passed",
    ),
    RuntimeGovernanceReasonCode(
        code="RG_MISSING_RUN_ID",
        category=FailureCategory.VALIDATION_FAILURE,
        severity=FailureSeverity.ERROR,
        retryable=False,
        description="missing run_id",
    ),
    RuntimeGovernanceReasonCode(
        code="RG_MISSING_ADAPTER_ID",
        category=FailureCategory.VALIDATION_FAILURE,
        severity=FailureSeverity.ERROR,
        retryable=False,
        description="missing adapter_id",
    ),
    RuntimeGovernanceReasonCode(
        code="RG_UNKNOWN_MODE",
        category=FailureCategory.VALIDATION_FAILURE,
        severity=FailureSeverity.ERROR,
        retryable=False,
        description="unknown governance mode",
    ),
    RuntimeGovernanceReasonCode(
        code="RG_SUBMIT_BLOCKED_NON_TEST",
        category=FailureCategory.POLICY_BLOCK,
        severity=FailureSeverity.CRITICAL,
        retryable=False,
        description="submit blocked outside test",
    ),
    RuntimeGovernanceReasonCode(
        code="RG_NETWORK_BLOCKED_MODE",
        category=FailureCategory.POLICY_BLOCK,
        severity=FailureSeverity.CRITICAL,
        retryable=False,
        description="network blocked without mode",
    ),
    RuntimeGovernanceReasonCode(
        code="RG_POLICY_BLOCK",
        category=FailureCategory.POLICY_BLOCK,
        severity=FailureSeverity.CRITICAL,
        retryable=False,
        description="general policy block",
    ),
    RuntimeGovernanceReasonCode(
        code="RG_UNKNOWN_FAILURE",
        category=FailureCategory.UNKNOWN,
        severity=FailureSeverity.ERROR,
        retryable=True,
        description="unknown governance failure",
    ),
]


def build_runtime_governance_reason_code_registry() -> List[RuntimeGovernanceReasonCode]:
    """Return a copy of the full reason code registry. No I/O."""
    return list(_REGISTRY)


def get_runtime_governance_reason_code(code: str) -> RuntimeGovernanceReasonCode:
    """Look up a reason code by its code string. Raises ValueError if not found. No I/O."""
    for rc in _REGISTRY:
        if rc.code == code:
            return rc
    raise ValueError(f"unknown governance reason code: {code!r}")


def reason_code_registry_to_dict(registry: List[RuntimeGovernanceReasonCode]) -> List[Dict[str, Any]]:
    """Serialize a reason code registry to a list of plain dicts. No I/O."""
    return [
        {
            "code": rc.code,
            "category": rc.category.value,
            "severity": rc.severity.value,
            "retryable": rc.retryable,
            "description": rc.description,
        }
        for rc in registry
    ]


def reason_code_registry_to_markdown(registry: List[RuntimeGovernanceReasonCode]) -> str:
    """Render a reason code registry as a Markdown table. No I/O."""
    lines = [
        "| Code | Category | Severity | Retryable | Description |",
        "|------|----------|----------|-----------|-------------|",
    ]
    for rc in registry:
        lines.append(
            f"| {rc.code} | {rc.category.value} | {rc.severity.value} | "
            f"{'yes' if rc.retryable else 'no'} | {rc.description} |"
        )
    return "\n".join(lines)
