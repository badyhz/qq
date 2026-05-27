"""Runtime governance engineering closeout bundle -- pre-live audit summary.

Aggregates all runtime governance pre-live audit artifacts into a single
closeout bundle. Pure. No I/O. No network. No random. Deterministic.

Final status logic:
  FAIL if any summary has a hard blocker (verdict/decision = FAIL or HOLD)
  WARN if any summary has a review item (verdict/decision = WARN or REVIEW)
  PASS if all summaries pass or are review-safe
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_stack_manifest import (
    build_expected_runtime_governance_stack_manifest,
    summarize_runtime_manifest,
)
from core.runtime_governance_regression_packet import (
    build_runtime_governance_regression_packet,
)
from core.runtime_governance_phase_control_report import (
    build_runtime_governance_phase_control_report,
)
from core.runtime_governance_manual_scope_packet import (
    build_runtime_governance_manual_scope_packet,
    summarize_manual_scope_packet,
)
from core.runtime_governance_integration_risk_register import (
    summarize_risk_register,
    build_runtime_governance_integration_risk_register,
)
from core.runtime_governance_artifact_index import (
    summarize_artifact_index,
    build_runtime_governance_artifact_index,
)
from core.runtime_governance_closeout_checklist import (
    summarize_closeout_checklist,
    build_runtime_governance_closeout_checklist,
)


# -- dataclass --


@dataclass(frozen=True)
class RuntimeGovernanceEngineeringCloseoutBundle:
    """Immutable engineering closeout bundle for runtime governance.

    Aggregates all pre-live audit artifact summaries into one bundle
    with a deterministic final status.
    """

    title: str
    stack_manifest_summary: Dict[str, Any]
    regression_summary: Dict[str, Any]
    phase_control_summary: Dict[str, Any]
    manual_scope_summary: Dict[str, Any]
    risk_register_summary: Dict[str, Any]
    artifact_index_summary: Dict[str, Any]
    closeout_summary: Dict[str, Any]
    final_status: str  # PASS / WARN / FAIL
    notes: List[str] = field(default_factory=list)


# -- status resolution --

_HARD_BLOCKER_VALUES = frozenset({"FAIL", "HOLD"})
_REVIEW_VALUES = frozenset({"WARN", "REVIEW", "PROCEED_TO_MANUAL_SCOPE_ONLY"})


def _resolve_final_status(summaries: List[Dict[str, Any]]) -> str:
    """Resolve final status from summary verdicts. Pure.

    FAIL if any summary verdict is in _HARD_BLOCKER_VALUES.
    WARN if any summary verdict is in _REVIEW_VALUES.
    PASS otherwise.
    """
    has_hard_blocker = False
    has_review = False

    for s in summaries:
        verdict = s.get("verdict") or s.get("final_verdict") or s.get("final_decision") or ""
        if verdict in _HARD_BLOCKER_VALUES:
            has_hard_blocker = True
        elif verdict in _REVIEW_VALUES:
            has_review = True

    if has_hard_blocker:
        return "FAIL"
    if has_review:
        return "WARN"
    return "PASS"


# -- builder --


def build_runtime_governance_engineering_closeout_bundle(
    *,
    title: str = "Runtime Governance Engineering Closeout Bundle",
) -> RuntimeGovernanceEngineeringCloseoutBundle:
    """Build engineering closeout bundle from default governance components.

    Pure. No I/O. Defaults produce all-pass sub-summaries.
    Final status is WARN because phase_control defaults to
    PROCEED_TO_MANUAL_SCOPE_ONLY (a review item).
    """
    # build sub-components with defaults (all pass)
    manifest = build_expected_runtime_governance_stack_manifest()
    stack_manifest_summary = summarize_runtime_manifest(manifest)

    regression = build_runtime_governance_regression_packet()
    regression_summary = {
        "total": regression.scenario_count,
        "pass": regression.scenario_pass_count,
        "fail": regression.scenario_fail_count,
        "verdict": regression.final_verdict,
    }

    phase_control = build_runtime_governance_phase_control_report()
    phase_control_summary = {
        "phase": phase_control.phase,
        "regression_verdict": phase_control.regression_verdict,
        "readiness_grade": phase_control.readiness_grade,
        "blocker_action": phase_control.blocker_action,
        "no_submit_verdict": phase_control.no_submit_verdict,
        "final_decision": phase_control.final_decision,
    }

    manual_scope = build_runtime_governance_manual_scope_packet()
    manual_scope_summary = summarize_manual_scope_packet(manual_scope)

    risk_register = build_runtime_governance_integration_risk_register()
    risk_register_summary = summarize_risk_register(risk_register)

    artifact_index = build_runtime_governance_artifact_index()
    artifact_index_summary = summarize_artifact_index(artifact_index)

    closeout_checklist = build_runtime_governance_closeout_checklist()
    closeout_summary = summarize_closeout_checklist(closeout_checklist)

    # collect notes
    notes: List[str] = []
    notes.extend(phase_control.notes)
    notes.extend(manual_scope.notes)
    notes.extend(risk_register.notes)
    notes.extend(artifact_index.notes)
    notes.extend(closeout_checklist.notes)

    # resolve final status
    all_summaries = [
        stack_manifest_summary,
        regression_summary,
        phase_control_summary,
        manual_scope_summary,
        risk_register_summary,
        artifact_index_summary,
        closeout_summary,
    ]
    final_status = _resolve_final_status(all_summaries)

    return RuntimeGovernanceEngineeringCloseoutBundle(
        title=title,
        stack_manifest_summary=stack_manifest_summary,
        regression_summary=regression_summary,
        phase_control_summary=phase_control_summary,
        manual_scope_summary=manual_scope_summary,
        risk_register_summary=risk_register_summary,
        artifact_index_summary=artifact_index_summary,
        closeout_summary=closeout_summary,
        final_status=final_status,
        notes=notes,
    )


# -- serialization --


def engineering_closeout_bundle_to_dict(
    bundle: RuntimeGovernanceEngineeringCloseoutBundle,
) -> Dict[str, Any]:
    """Serialize bundle to a plain dict. Deterministic."""
    return {
        "title": bundle.title,
        "stack_manifest_summary": dict(bundle.stack_manifest_summary),
        "regression_summary": dict(bundle.regression_summary),
        "phase_control_summary": dict(bundle.phase_control_summary),
        "manual_scope_summary": dict(bundle.manual_scope_summary),
        "risk_register_summary": dict(bundle.risk_register_summary),
        "artifact_index_summary": dict(bundle.artifact_index_summary),
        "closeout_summary": dict(bundle.closeout_summary),
        "final_status": bundle.final_status,
        "notes": list(bundle.notes),
    }


def engineering_closeout_bundle_to_markdown(
    bundle: RuntimeGovernanceEngineeringCloseoutBundle,
) -> str:
    """Render bundle as deterministic markdown. No timestamps."""
    lines: List[str] = []

    lines.append(f"# {bundle.title}")
    lines.append("")
    lines.append(f"**Final Status:** {bundle.final_status}")
    lines.append("")

    # stack manifest
    lines.append("## Stack Manifest")
    lines.append("")
    sm = bundle.stack_manifest_summary
    lines.append(f"- **Total:** {sm.get('total', 'N/A')}")
    lines.append(f"- **Completed:** {sm.get('completed', 'N/A')}")
    lines.append(f"- **Verdict:** {sm.get('verdict', 'N/A')}")
    lines.append("")

    # regression
    lines.append("## Regression Packet")
    lines.append("")
    rg = bundle.regression_summary
    lines.append(f"- **Total Scenarios:** {rg.get('total', 'N/A')}")
    lines.append(f"- **Pass:** {rg.get('pass', 'N/A')}")
    lines.append(f"- **Fail:** {rg.get('fail', 'N/A')}")
    lines.append(f"- **Verdict:** {rg.get('verdict', 'N/A')}")
    lines.append("")

    # phase control
    lines.append("## Phase Control Report")
    lines.append("")
    pc = bundle.phase_control_summary
    lines.append(f"- **Phase:** {pc.get('phase', 'N/A')}")
    lines.append(f"- **Regression Verdict:** {pc.get('regression_verdict', 'N/A')}")
    lines.append(f"- **Readiness Grade:** {pc.get('readiness_grade', 'N/A')}")
    lines.append(f"- **Blocker Action:** {pc.get('blocker_action', 'N/A')}")
    lines.append(f"- **No-Submit Verdict:** {pc.get('no_submit_verdict', 'N/A')}")
    lines.append(f"- **Final Decision:** {pc.get('final_decision', 'N/A')}")
    lines.append("")

    # manual scope
    lines.append("## Manual Scope Packet")
    lines.append("")
    ms = bundle.manual_scope_summary
    lines.append(f"- **Item Count:** {ms.get('item_count', 'N/A')}")
    lines.append(f"- **Verdict:** {ms.get('verdict', 'N/A')}")
    lines.append("")

    # risk register
    lines.append("## Integration Risk Register")
    lines.append("")
    rr = bundle.risk_register_summary
    lines.append(f"- **Total Risks:** {rr.get('total', 'N/A')}")
    lines.append(f"- **By Status:** {rr.get('by_status', {})}")
    lines.append(f"- **Verdict:** {rr.get('verdict', 'N/A')}")
    lines.append("")

    # artifact index
    lines.append("## Artifact Index")
    lines.append("")
    ai = bundle.artifact_index_summary
    lines.append(f"- **Total Artifacts:** {ai.get('total', 'N/A')}")
    lines.append(f"- **By Status:** {ai.get('by_status', {})}")
    lines.append(f"- **Verdict:** {ai.get('verdict', 'N/A')}")
    lines.append("")

    # closeout checklist
    lines.append("## Closeout Checklist")
    lines.append("")
    cs = bundle.closeout_summary
    lines.append(f"- **Total Items:** {cs.get('total', 'N/A')}")
    lines.append(f"- **By Status:** {cs.get('by_status', {})}")
    lines.append(f"- **Verdict:** {cs.get('verdict', 'N/A')}")
    lines.append("")

    # notes
    if bundle.notes:
        lines.append("## Notes")
        lines.append("")
        for note in bundle.notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
