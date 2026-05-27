"""Evaluate scenario catalog through preflight packet builder.

Pure. No I/O. No network. No random. No timestamps. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.runtime_governance_scenario_catalog import (
    RuntimeGovernanceScenario,
    build_runtime_governance_scenario_catalog,
)
from core.runtime_governance_preflight_packet import (
    build_runtime_governance_preflight_packet,
)


@dataclass(frozen=True)
class RuntimeGovernanceScenarioEvaluation:
    scenario_id: str
    expected_verdict: str
    actual_verdict: str
    expected_ready_for_runtime: bool
    actual_ready_for_runtime: bool
    ok: bool
    notes: List[str]


# ── evaluator ──────────────────────────────────────────────────────────


def evaluate_runtime_governance_scenario(
    scenario: RuntimeGovernanceScenario,
) -> RuntimeGovernanceScenarioEvaluation:
    """Evaluate a single scenario by building its preflight packet.

    ok=True only if both verdict and ready_for_runtime match expected.
    """
    packet = build_runtime_governance_preflight_packet(scenario.input)

    actual_verdict = packet.final_verdict
    actual_ready = packet.proceed

    verdict_match = actual_verdict == scenario.expected_verdict
    ready_match = actual_ready == scenario.expected_ready_for_runtime
    ok = verdict_match and ready_match

    notes: List[str] = []
    if not verdict_match:
        notes.append(
            f"verdict mismatch: expected={scenario.expected_verdict!r} "
            f"actual={actual_verdict!r}"
        )
    if not ready_match:
        notes.append(
            f"ready mismatch: expected={scenario.expected_ready_for_runtime!r} "
            f"actual={actual_ready!r}"
        )

    return RuntimeGovernanceScenarioEvaluation(
        scenario_id=scenario.scenario_id,
        expected_verdict=scenario.expected_verdict,
        actual_verdict=actual_verdict,
        expected_ready_for_runtime=scenario.expected_ready_for_runtime,
        actual_ready_for_runtime=actual_ready,
        ok=ok,
        notes=notes,
    )


def evaluate_runtime_governance_scenario_catalog(
    catalog: List[RuntimeGovernanceScenario] | None = None,
) -> List[RuntimeGovernanceScenarioEvaluation]:
    """Evaluate all scenarios in the catalog. Default = full 8-scenario catalog."""
    if catalog is None:
        catalog = build_runtime_governance_scenario_catalog()
    return [evaluate_runtime_governance_scenario(s) for s in catalog]


# ── serialization ──────────────────────────────────────────────────────


def scenario_evaluations_to_dict(
    evaluations: List[RuntimeGovernanceScenarioEvaluation],
) -> List[Dict[str, Any]]:
    """Serialize evaluations to plain dicts. Deterministic."""
    result: List[Dict[str, Any]] = []
    for e in evaluations:
        result.append(
            {
                "scenario_id": e.scenario_id,
                "expected_verdict": e.expected_verdict,
                "actual_verdict": e.actual_verdict,
                "expected_ready_for_runtime": e.expected_ready_for_runtime,
                "actual_ready_for_runtime": e.actual_ready_for_runtime,
                "ok": e.ok,
                "notes": list(e.notes),
            }
        )
    return result


def scenario_evaluations_to_markdown(
    evaluations: List[RuntimeGovernanceScenarioEvaluation],
) -> str:
    """Render evaluations as a deterministic Markdown table."""
    lines = [
        "# Runtime Governance Scenario Evaluations",
        "",
        "| scenario_id | expected_verdict | actual_verdict | expected_ready | actual_ready | ok |",
        "|---|---|---|---|---|---|",
    ]
    for e in evaluations:
        lines.append(
            f"| {e.scenario_id} | {e.expected_verdict} | {e.actual_verdict} "
            f"| {e.expected_ready_for_runtime} | {e.actual_ready_for_runtime} | {e.ok} |"
        )
    lines.append("")
    return "\n".join(lines)
