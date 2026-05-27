"""Runtime governance input contract — pure data definitions and validation.

Deterministic. No timestamps. No random. No I/O. No network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.governance_failure_taxonomy import (
    FailureCategory,
    FailureSeverity,
    GovernanceFailure,
    classify_governance_failure,
)


ALLOWED_MODES = frozenset({"shadow", "dry_run", "testnet_dry", "testnet_submit_simulated"})


@dataclass(frozen=True)
class RuntimeGovernanceInput:
    """Input contract for runtime governance checks."""

    run_id: str
    adapter_id: str
    mode: str
    requested_action: str
    symbol: str
    environment: str
    allow_network: bool
    allow_submit: bool
    allow_file_io: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeGovernanceContractResult:
    """Result of validating a RuntimeGovernanceInput."""

    ok: bool
    failures: List[GovernanceFailure]
    normalized_input: Optional[RuntimeGovernanceInput]
    notes: List[str]


# ── pure functions ───────────────────────────────────────────────────


def normalize_runtime_governance_input(
    *,
    run_id: str = "",
    adapter_id: str = "",
    mode: str = "",
    requested_action: str = "",
    symbol: str = "",
    environment: str = "",
    allow_network: bool = False,
    allow_submit: bool = False,
    allow_file_io: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> RuntimeGovernanceInput:
    """Build a RuntimeGovernanceInput from loose kwargs. No I/O."""
    return RuntimeGovernanceInput(
        run_id=str(run_id),
        adapter_id=str(adapter_id),
        mode=str(mode),
        requested_action=str(requested_action),
        symbol=str(symbol),
        environment=str(environment),
        allow_network=bool(allow_network),
        allow_submit=bool(allow_submit),
        allow_file_io=bool(allow_file_io),
        metadata=dict(metadata) if metadata else {},
    )


def validate_runtime_governance_input(
    inp: RuntimeGovernanceInput,
) -> RuntimeGovernanceContractResult:
    """Validate a RuntimeGovernanceInput against policy rules.

    Deterministic. No I/O. Returns all failures found.
    """
    failures: List[GovernanceFailure] = []
    notes: List[str] = []

    # structural validation
    if not inp.run_id:
        failures.append(
            classify_governance_failure(
                category=FailureCategory.VALIDATION_FAILURE,
                severity=FailureSeverity.ERROR,
                message="missing run_id",
                source="runtime_governance_contract",
            )
        )

    if not inp.adapter_id:
        failures.append(
            classify_governance_failure(
                category=FailureCategory.VALIDATION_FAILURE,
                severity=FailureSeverity.ERROR,
                message="missing adapter_id",
                source="runtime_governance_contract",
            )
        )

    if inp.mode not in ALLOWED_MODES:
        failures.append(
            classify_governance_failure(
                category=FailureCategory.VALIDATION_FAILURE,
                severity=FailureSeverity.ERROR,
                message=f"unknown mode: {inp.mode}",
                source="runtime_governance_contract",
            )
        )

    # policy blocks
    if inp.allow_submit and inp.environment != "test":
        failures.append(
            classify_governance_failure(
                category=FailureCategory.POLICY_BLOCK,
                severity=FailureSeverity.CRITICAL,
                message="allow_submit=True in non-test environment",
                source="runtime_governance_contract",
            )
        )

    if inp.allow_network and not inp.mode:
        failures.append(
            classify_governance_failure(
                category=FailureCategory.POLICY_BLOCK,
                severity=FailureSeverity.CRITICAL,
                message="allow_network=True without explicit mode",
                source="runtime_governance_contract",
            )
        )

    ok = len(failures) == 0
    if ok:
        notes.append("input valid")

    return RuntimeGovernanceContractResult(
        ok=ok,
        failures=failures,
        normalized_input=inp if ok else None,
        notes=notes,
    )


def runtime_governance_input_to_dict(inp: RuntimeGovernanceInput) -> Dict[str, Any]:
    """Serialize RuntimeGovernanceInput to a plain dict. No I/O."""
    return {
        "run_id": inp.run_id,
        "adapter_id": inp.adapter_id,
        "mode": inp.mode,
        "requested_action": inp.requested_action,
        "symbol": inp.symbol,
        "environment": inp.environment,
        "allow_network": inp.allow_network,
        "allow_submit": inp.allow_submit,
        "allow_file_io": inp.allow_file_io,
        "metadata": dict(inp.metadata),
    }
