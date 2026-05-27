"""T831 — Read-only scenario catalog for runtime governance."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyScenario:
    scenario_id: str
    description: str
    permission_envelope_kind: str  # kind for build_runtime_governance_permission_envelope
    expected_verdict: str  # "PASS" or "BLOCKED"
    expected_blocked: bool
    tags: List[str] = field(default_factory=list)


_CATALOG: List[RuntimeGovernanceReadOnlyScenario] = [
    RuntimeGovernanceReadOnlyScenario(
        scenario_id="safe_summary_read",
        description="Read account summary — safe read-only operation",
        permission_envelope_kind="account_summary_read",
        expected_verdict="PASS",
        expected_blocked=False,
        tags=["safe", "read"],
    ),
    RuntimeGovernanceReadOnlyScenario(
        scenario_id="unsafe_network",
        description="Outbound network call — violates read-only boundary",
        permission_envelope_kind="network_egress",
        expected_verdict="BLOCKED",
        expected_blocked=True,
        tags=["unsafe", "network"],
    ),
    RuntimeGovernanceReadOnlyScenario(
        scenario_id="unsafe_write",
        description="Filesystem write — violates read-only boundary",
        permission_envelope_kind="filesystem_write",
        expected_verdict="BLOCKED",
        expected_blocked=True,
        tags=["unsafe", "write"],
    ),
    RuntimeGovernanceReadOnlyScenario(
        scenario_id="unsafe_order",
        description="Order submission — violates read-only boundary",
        permission_envelope_kind="order_submit",
        expected_verdict="BLOCKED",
        expected_blocked=True,
        tags=["unsafe", "order"],
    ),
    RuntimeGovernanceReadOnlyScenario(
        scenario_id="unsafe_secret",
        description="Secret/credential access — violates read-only boundary",
        permission_envelope_kind="secret_access",
        expected_verdict="BLOCKED",
        expected_blocked=True,
        tags=["unsafe", "secret"],
    ),
    RuntimeGovernanceReadOnlyScenario(
        scenario_id="unsafe_account_mutation",
        description="Account state mutation — violates read-only boundary",
        permission_envelope_kind="account_mutation",
        expected_verdict="BLOCKED",
        expected_blocked=True,
        tags=["unsafe", "mutation"],
    ),
]

_INDEX: Dict[str, RuntimeGovernanceReadOnlyScenario] = {
    s.scenario_id: s for s in _CATALOG
}


def build_readonly_scenario_catalog() -> List[RuntimeGovernanceReadOnlyScenario]:
    """Build catalog. Deterministic."""
    return list(_CATALOG)


def get_readonly_scenario(scenario_id: str) -> RuntimeGovernanceReadOnlyScenario:
    """Lookup. Raises ValueError if not found."""
    if scenario_id not in _INDEX:
        raise ValueError(f"Unknown scenario_id: {scenario_id!r}")
    return _INDEX[scenario_id]


def readonly_scenario_catalog_to_dict(
    catalog: List[RuntimeGovernanceReadOnlyScenario],
) -> List[Dict[str, Any]]:
    """Serialize."""
    return [
        {
            "scenario_id": s.scenario_id,
            "description": s.description,
            "permission_envelope_kind": s.permission_envelope_kind,
            "expected_verdict": s.expected_verdict,
            "expected_blocked": s.expected_blocked,
            "tags": list(s.tags),
        }
        for s in catalog
    ]


def readonly_scenario_catalog_to_markdown(
    catalog: List[RuntimeGovernanceReadOnlyScenario],
) -> str:
    """Deterministic markdown."""
    lines = ["# Read-Only Scenario Catalog", ""]
    lines.append("| scenario_id | description | envelope_kind | verdict | blocked | tags |")
    lines.append("|---|---|---|---|---|---|")
    for s in catalog:
        tags = ", ".join(s.tags)
        lines.append(
            f"| {s.scenario_id} | {s.description} | {s.permission_envelope_kind} "
            f"| {s.expected_verdict} | {s.expected_blocked} | {tags} |"
        )
    lines.append("")
    return "\n".join(lines)
