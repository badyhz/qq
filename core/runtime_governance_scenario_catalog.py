"""Deterministic scenario definitions for runtime governance preflight testing.

No I/O. No timestamps. No randomness. Pure data + pure functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.runtime_governance_contract import (
    ALLOWED_MODES,
    RuntimeGovernanceInput,
    normalize_runtime_governance_input,
    validate_runtime_governance_input,
)
from core.governance_failure_taxonomy import FailureCategory


@dataclass(frozen=True)
class RuntimeGovernanceScenario:
    scenario_id: str
    name: str
    input: RuntimeGovernanceInput
    expected_verdict: str  # PASS / FAIL / BLOCKED
    expected_ready_for_runtime: bool
    tags: List[str]  # sorted
    notes: str


# ── internal builders ─────────────────────────────────────────────────


def _build_catalog() -> List[RuntimeGovernanceScenario]:
    """Build the 8 deterministic scenarios. Order is fixed."""
    raw: List[Dict[str, Any]] = [
        {
            "scenario_id": "valid_shadow",
            "name": "Valid shadow run",
            "kwargs": dict(
                run_id="run-001",
                adapter_id="adapter-001",
                mode="shadow",
                requested_action="scan",
                symbol="BTCUSDT",
                environment="local",
                allow_network=False,
                allow_submit=False,
                allow_file_io=False,
            ),
            "expected_verdict": "PASS",
            "expected_ready_for_runtime": True,
            "tags": ["shadow", "valid"],
            "notes": "Minimal valid shadow scenario.",
        },
        {
            "scenario_id": "valid_dry_run",
            "name": "Valid dry run",
            "kwargs": dict(
                run_id="run-002",
                adapter_id="adapter-002",
                mode="dry_run",
                requested_action="scan",
                symbol="ETHUSDT",
                environment="local",
                allow_network=False,
                allow_submit=False,
                allow_file_io=False,
            ),
            "expected_verdict": "PASS",
            "expected_ready_for_runtime": True,
            "tags": ["dry_run", "valid"],
            "notes": "Minimal valid dry-run scenario.",
        },
        {
            "scenario_id": "missing_run_id",
            "name": "Missing run_id",
            "kwargs": dict(
                run_id="",
                adapter_id="adapter-003",
                mode="shadow",
                requested_action="scan",
                symbol="BTCUSDT",
                environment="local",
                allow_network=False,
                allow_submit=False,
                allow_file_io=False,
            ),
            "expected_verdict": "FAIL",
            "expected_ready_for_runtime": False,
            "tags": ["validation", "fail"],
            "notes": "Empty run_id triggers VALIDATION_FAILURE.",
        },
        {
            "scenario_id": "missing_adapter_id",
            "name": "Missing adapter_id",
            "kwargs": dict(
                run_id="run-004",
                adapter_id="",
                mode="shadow",
                requested_action="scan",
                symbol="BTCUSDT",
                environment="local",
                allow_network=False,
                allow_submit=False,
                allow_file_io=False,
            ),
            "expected_verdict": "FAIL",
            "expected_ready_for_runtime": False,
            "tags": ["validation", "fail"],
            "notes": "Empty adapter_id triggers VALIDATION_FAILURE.",
        },
        {
            "scenario_id": "submit_blocked_prod",
            "name": "Submit blocked in prod",
            "kwargs": dict(
                run_id="run-005",
                adapter_id="adapter-005",
                mode="shadow",
                requested_action="submit",
                symbol="BTCUSDT",
                environment="prod",
                allow_network=False,
                allow_submit=True,
                allow_file_io=False,
            ),
            "expected_verdict": "BLOCKED",
            "expected_ready_for_runtime": False,
            "tags": ["policy", "blocked"],
            "notes": "allow_submit=True in non-test env triggers POLICY_BLOCK.",
        },
        {
            "scenario_id": "network_blocked_without_explicit_mode",
            "name": "Network without explicit mode",
            "kwargs": dict(
                run_id="run-006",
                adapter_id="adapter-006",
                mode="",
                requested_action="scan",
                symbol="BTCUSDT",
                environment="local",
                allow_network=True,
                allow_submit=False,
                allow_file_io=False,
            ),
            "expected_verdict": "BLOCKED",
            "expected_ready_for_runtime": False,
            "tags": ["policy", "blocked"],
            "notes": "allow_network=True without mode triggers POLICY_BLOCK.",
        },
        {
            "scenario_id": "unknown_mode",
            "name": "Unknown mode value",
            "kwargs": dict(
                run_id="run-007",
                adapter_id="adapter-007",
                mode="bogus",
                requested_action="scan",
                symbol="BTCUSDT",
                environment="local",
                allow_network=False,
                allow_submit=False,
                allow_file_io=False,
            ),
            "expected_verdict": "FAIL",
            "expected_ready_for_runtime": False,
            "tags": ["validation", "fail"],
            "notes": "Mode not in ALLOWED_MODES triggers VALIDATION_FAILURE.",
        },
        {
            "scenario_id": "blocked_policy",
            "name": "Shadow with submit in prod",
            "kwargs": dict(
                run_id="run-008",
                adapter_id="adapter-008",
                mode="shadow",
                requested_action="submit",
                symbol="BTCUSDT",
                environment="prod",
                allow_network=False,
                allow_submit=True,
                allow_file_io=False,
            ),
            "expected_verdict": "BLOCKED",
            "expected_ready_for_runtime": False,
            "tags": ["policy", "blocked"],
            "notes": "Shadow mode but allow_submit=True in prod → POLICY_BLOCK.",
        },
    ]

    scenarios: List[RuntimeGovernanceScenario] = []
    for entry in raw:
        scenarios.append(
            RuntimeGovernanceScenario(
                scenario_id=entry["scenario_id"],
                name=entry["name"],
                input=normalize_runtime_governance_input(**entry["kwargs"]),
                expected_verdict=entry["expected_verdict"],
                expected_ready_for_runtime=entry["expected_ready_for_runtime"],
                tags=sorted(entry["tags"]),
                notes=entry["notes"],
            )
        )
    return scenarios


# ── public API ────────────────────────────────────────────────────────


def build_runtime_governance_scenario_catalog() -> List[RuntimeGovernanceScenario]:
    """Return the full deterministic scenario catalog (8 items)."""
    return list(_build_catalog())


def get_runtime_governance_scenario(scenario_id: str) -> RuntimeGovernanceScenario:
    """Lookup by scenario_id. Raises ValueError if not found."""
    for s in _build_catalog():
        if s.scenario_id == scenario_id:
            return s
    raise ValueError(f"unknown scenario_id: {scenario_id!r}")


def scenario_catalog_to_dict(
    catalog: List[RuntimeGovernanceScenario],
) -> List[Dict[str, Any]]:
    """Serialize catalog to a list of plain dicts. Deterministic."""
    from core.runtime_governance_contract import runtime_governance_input_to_dict

    result: List[Dict[str, Any]] = []
    for s in catalog:
        result.append(
            {
                "scenario_id": s.scenario_id,
                "name": s.name,
                "input": runtime_governance_input_to_dict(s.input),
                "expected_verdict": s.expected_verdict,
                "expected_ready_for_runtime": s.expected_ready_for_runtime,
                "tags": list(s.tags),
                "notes": s.notes,
            }
        )
    return result


def scenario_catalog_to_markdown(
    catalog: List[RuntimeGovernanceScenario],
) -> str:
    """Render catalog as a Markdown table. Deterministic."""
    lines = [
        "# Runtime Governance Scenario Catalog",
        "",
        "| scenario_id | name | mode | verdict | ready | tags |",
        "|---|---|---|---|---|---|",
    ]
    for s in catalog:
        tags_str = ", ".join(s.tags)
        lines.append(
            f"| {s.scenario_id} | {s.name} | {s.input.mode or '(empty)'} "
            f"| {s.expected_verdict} | {s.expected_ready_for_runtime} | {tags_str} |"
        )
    lines.append("")
    return "\n".join(lines)
