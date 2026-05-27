"""Runtime governance policy matrix.

Pure policy matrix for mode/environment/allow flags.
No side effects. No I/O. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

MODES = ("shadow", "dry_run", "testnet_dry", "testnet_submit_simulated")
ENVIRONMENTS = ("local", "test", "testnet", "prod")


@dataclass(frozen=True)
class RuntimeGovernancePolicyCase:
    mode: str
    environment: str
    allow_network: bool
    allow_submit: bool
    allow_file_io: bool
    expected_allowed: bool
    expected_reason: str


def evaluate_runtime_governance_policy_case(
    mode: str,
    environment: str,
    allow_network: bool,
    allow_submit: bool,
    allow_file_io: bool,
) -> Tuple[bool, str]:
    """Evaluate a single policy case.

    Returns (expected_allowed, expected_reason).
    """
    # --- env-level blocks (highest priority) ---
    if environment == "prod":
        return False, "prod environment: submit always blocked"

    if environment == "local":
        return False, "local environment: submit blocked for all modes"

    # --- mode-level blocks ---
    if mode == "shadow":
        if allow_submit:
            return False, "shadow mode: no submit ever"
        if allow_network:
            return False, "shadow mode: no network unless explicitly allowed"
        if allow_file_io:
            return False, "shadow mode: file_io false by default"
        return True, "shadow mode: offline only"

    if mode == "dry_run":
        if allow_submit:
            return False, "dry_run mode: no submit ever"
        if allow_network:
            return False, "dry_run mode: no network unless explicitly allowed"
        return True, "dry_run mode: no submit, no network"

    if mode == "testnet_dry":
        if allow_submit:
            return False, "testnet_dry mode: no submit"
        if environment in ("test", "testnet"):
            return True, "testnet_dry mode: network ok in test/testnet"
        return False, f"testnet_dry mode: unexpected environment {environment}"

    if mode == "testnet_submit_simulated":
        if allow_submit and environment in ("test", "testnet"):
            return True, "testnet_submit_simulated: submit allowed in test/testnet"
        if allow_submit:
            return False, f"testnet_submit_simulated: submit blocked in {environment}"
        return True, "testnet_submit_simulated: no submit requested"

    return False, f"unknown mode: {mode}"


def build_runtime_governance_policy_matrix() -> List[RuntimeGovernancePolicyCase]:
    """Build the full policy matrix covering key mode/env/flag combinations."""
    matrix: List[RuntimeGovernancePolicyCase] = []

    def _add(mode, env, net, sub, fio):
        allowed, reason = evaluate_runtime_governance_policy_case(
            mode, env, net, sub, fio,
        )
        matrix.append(
            RuntimeGovernancePolicyCase(
                mode=mode,
                environment=env,
                allow_network=net,
                allow_submit=sub,
                allow_file_io=fio,
                expected_allowed=allowed,
                expected_reason=reason,
            )
        )

    # shadow — no submit, no network, no file_io
    _add("shadow", "local", False, False, False)
    _add("shadow", "test", False, False, False)
    _add("shadow", "testnet", False, False, False)
    _add("shadow", "prod", False, False, False)

    # dry_run — no submit, no network
    _add("dry_run", "local", False, False, False)
    _add("dry_run", "test", False, False, False)
    _add("dry_run", "testnet", False, False, False)
    _add("dry_run", "prod", False, False, False)

    # testnet_dry — no submit, network ok in test/testnet
    _add("testnet_dry", "local", True, False, False)
    _add("testnet_dry", "test", True, False, False)
    _add("testnet_dry", "testnet", True, False, False)
    _add("testnet_dry", "prod", True, False, False)

    # testnet_submit_simulated — submit allowed only in test/testnet
    _add("testnet_submit_simulated", "local", True, True, False)
    _add("testnet_submit_simulated", "test", True, True, False)
    _add("testnet_submit_simulated", "testnet", True, True, False)
    _add("testnet_submit_simulated", "prod", True, True, False)

    return matrix


def policy_matrix_to_dict(
    matrix: List[RuntimeGovernancePolicyCase],
) -> List[Dict]:
    """Convert policy matrix to list of dicts."""
    return [
        {
            "mode": c.mode,
            "environment": c.environment,
            "allow_network": c.allow_network,
            "allow_submit": c.allow_submit,
            "allow_file_io": c.allow_file_io,
            "expected_allowed": c.expected_allowed,
            "expected_reason": c.expected_reason,
        }
        for c in matrix
    ]


def policy_matrix_to_markdown(
    matrix: List[RuntimeGovernancePolicyCase],
) -> str:
    """Convert policy matrix to markdown table."""
    lines = [
        "# Runtime Governance Policy Matrix",
        "",
        "| # | mode | env | network | submit | file_io | allowed | reason |",
        "|--:|------|-----|---------|--------|---------|---------|--------|",
    ]
    for i, c in enumerate(matrix, 1):
        lines.append(
            f"| {i} | {c.mode} | {c.environment} "
            f"| {c.allow_network} | {c.allow_submit} | {c.allow_file_io} "
            f"| {c.expected_allowed} | {c.expected_reason} |"
        )
    return "\n".join(lines) + "\n"
