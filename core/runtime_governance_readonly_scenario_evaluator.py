"""T834 — Runtime governance read-only scenario evaluator.

Deterministic. No I/O. No timestamps. No random. Frozen dataclass.
Evaluates read-only scenarios through permission envelopes and invariants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_permission_envelope import (
    RuntimeGovernancePermissionEnvelope,
    evaluate_permission_envelope_raw,
)
from core.runtime_governance_readonly_invariant_checker import (
    check_readonly_permission_invariants,
)
from core.runtime_governance_readonly_scenario_catalog import (
    RuntimeGovernanceReadOnlyScenario,
    build_readonly_scenario_catalog,
)


# ── envelope kind -> flags mapping ──────────────────────────────────

_KIND_FLAGS: Dict[str, Dict[str, bool]] = {
    "account_summary_read": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": False,
        "allow_order": False,
        "allow_account_mutation": False,
        "allow_secret_access": False,
    },
    "network_egress": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": True,
        "allow_order": False,
        "allow_account_mutation": False,
        "allow_secret_access": False,
    },
    "filesystem_write": {
        "allow_read": True,
        "allow_write": True,
        "allow_network": False,
        "allow_order": False,
        "allow_account_mutation": False,
        "allow_secret_access": False,
    },
    "order_submit": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": False,
        "allow_order": True,
        "allow_account_mutation": False,
        "allow_secret_access": False,
    },
    "secret_access": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": False,
        "allow_order": False,
        "allow_account_mutation": False,
        "allow_secret_access": True,
    },
    "account_mutation": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": False,
        "allow_order": False,
        "allow_account_mutation": True,
        "allow_secret_access": False,
    },
}


def _build_envelope(kind: str) -> RuntimeGovernancePermissionEnvelope:
    """Build envelope from kind. Deterministic."""
    if kind not in _KIND_FLAGS:
        raise ValueError(f"Unknown envelope kind: {kind!r}")
    flags = _KIND_FLAGS[kind]
    verdict = evaluate_permission_envelope_raw(**flags)
    return RuntimeGovernancePermissionEnvelope(
        **flags,
        reason=f"scenario_kind:{kind}",
        verdict=verdict,
    )


# ── result dataclass ────────────────────────────────────────────────


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyScenarioEvaluation:
    """Evaluation result for a single read-only scenario."""

    scenario_id: str
    expected_verdict: str
    actual_verdict: str
    expected_blocked: bool
    actual_blocked: bool
    ok: bool
    notes: List[str] = field(default_factory=list)


# ── evaluation ──────────────────────────────────────────────────────


def evaluate_readonly_scenario(
    scenario: RuntimeGovernanceReadOnlyScenario,
) -> RuntimeGovernanceReadOnlyScenarioEvaluation:
    """Evaluate a single scenario through envelope + invariants. Pure."""
    envelope = _build_envelope(scenario.permission_envelope_kind)
    actual_verdict = evaluate_permission_envelope_raw(
        allow_read=envelope.allow_read,
        allow_write=envelope.allow_write,
        allow_network=envelope.allow_network,
        allow_order=envelope.allow_order,
        allow_account_mutation=envelope.allow_account_mutation,
        allow_secret_access=envelope.allow_secret_access,
    )
    invariants = check_readonly_permission_invariants(envelope)

    notes: List[str] = []
    for inv in invariants:
        status = "ok" if inv.ok else inv.severity
        notes.append(f"{inv.invariant_id}: {status}")

    actual_blocked = actual_verdict == "BLOCKED"
    ok = actual_verdict == scenario.expected_verdict

    return RuntimeGovernanceReadOnlyScenarioEvaluation(
        scenario_id=scenario.scenario_id,
        expected_verdict=scenario.expected_verdict,
        actual_verdict=actual_verdict,
        expected_blocked=scenario.expected_blocked,
        actual_blocked=actual_blocked,
        ok=ok,
        notes=notes,
    )


# ── catalog evaluation ──────────────────────────────────────────────


def evaluate_readonly_scenario_catalog() -> (
    List[RuntimeGovernanceReadOnlyScenarioEvaluation]
):
    """Evaluate full catalog. Deterministic."""
    catalog = build_readonly_scenario_catalog()
    return [evaluate_readonly_scenario(s) for s in catalog]


# ── serialization ───────────────────────────────────────────────────


def readonly_evaluations_to_dict(
    evaluations: List[RuntimeGovernanceReadOnlyScenarioEvaluation],
) -> List[Dict[str, Any]]:
    """Serialize evaluations to list of dicts. Deterministic."""
    return [
        {
            "scenario_id": e.scenario_id,
            "expected_verdict": e.expected_verdict,
            "actual_verdict": e.actual_verdict,
            "expected_blocked": e.expected_blocked,
            "actual_blocked": e.actual_blocked,
            "ok": e.ok,
            "notes": list(e.notes),
        }
        for e in evaluations
    ]


def readonly_evaluations_to_markdown(
    evaluations: List[RuntimeGovernanceReadOnlyScenarioEvaluation],
) -> str:
    """Render evaluations as markdown table. Deterministic. No timestamps."""
    lines: List[str] = [
        "# Read-Only Scenario Evaluations",
        "",
        "| scenario_id | expected | actual | blocked | ok | notes |",
        "|---|---|---|---|---|---|",
    ]
    for e in evaluations:
        ok_sym = "PASS" if e.ok else "FAIL"
        blocked_sym = "yes" if e.actual_blocked else "no"
        notes_str = "; ".join(e.notes) if e.notes else ""
        lines.append(
            f"| {e.scenario_id} | {e.expected_verdict} | {e.actual_verdict} "
            f"| {blocked_sym} | {ok_sym} | {notes_str} |"
        )
    lines.append("")
    return "\n".join(lines)
