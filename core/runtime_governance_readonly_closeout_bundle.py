"""T841: Runtime governance read-only closeout bundle.

Bundle Wave A-B read-only artifacts into one deterministic summary.
Pure. No I/O. No timestamps. No random.

Final status logic:
  FAIL if any summary verdict is FAIL or HOLD
  WARN if any summary verdict is WARN or REVIEW
  PASS otherwise
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_readonly_stack_manifest import (
    build_readonly_stack_manifest,
    summarize_readonly_stack_manifest,
)
from core.runtime_governance_readonly_regression_packet import (
    build_readonly_regression_packet,
    readonly_regression_packet_to_dict,
)
from core.runtime_governance_readonly_readiness_score import (
    compute_readonly_readiness_score,
    readonly_readiness_score_to_dict,
)
from core.runtime_governance_readonly_blocker_summary import (
    summarize_readonly_blockers,
    readonly_blocker_summary_to_dict,
)
from core.runtime_governance_readonly_evidence_packet import (
    build_readonly_evidence_packet,
)
from core.runtime_governance_readonly_transition_checklist import (
    build_readonly_transition_checklist,
    summarize_readonly_transition_checklist,
)


# -- dataclass --


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyCloseoutBundle:
    """Immutable read-only closeout bundle aggregating Wave A-B artifacts."""

    manifest_summary: Dict[str, Any]
    regression_summary: Dict[str, Any]
    readiness_summary: Dict[str, Any]
    blocker_summary: Dict[str, Any]
    evidence_summary: Dict[str, Any]
    checklist_summary: Dict[str, Any]
    final_status: str  # PASS / WARN / FAIL
    notes: List[str] = field(default_factory=list)


# -- status resolution --

_HARD_BLOCKER_VALUES = frozenset({"FAIL", "HOLD"})
_REVIEW_VALUES = frozenset({"WARN", "REVIEW"})


def _resolve_final_status(summaries: List[Dict[str, Any]]) -> str:
    """Resolve final status from summary verdicts. Pure."""
    has_hard_blocker = False
    has_review = False

    for s in summaries:
        verdict = (
            s.get("verdict")
            or s.get("final_verdict")
            or s.get("recommended_action")
            or ""
        )
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


def build_readonly_closeout_bundle() -> RuntimeGovernanceReadOnlyCloseoutBundle:
    """Build read-only closeout bundle from default sub-components.

    Pure. No I/O. Defaults produce all-pass sub-summaries.
    """
    # manifest
    manifest = build_readonly_stack_manifest()
    manifest_summary = summarize_readonly_stack_manifest(manifest)

    # regression
    regression = build_readonly_regression_packet()
    regression_summary = readonly_regression_packet_to_dict(regression)

    # readiness
    readiness = compute_readonly_readiness_score(regression)
    readiness_summary = readonly_readiness_score_to_dict(readiness)

    # blockers
    blocker = summarize_readonly_blockers()
    blocker_summary = readonly_blocker_summary_to_dict(blocker)

    # evidence
    evidence_list = build_readonly_evidence_packet()
    evidence_summary = {
        "total": len(evidence_list),
        "pass": sum(1 for e in evidence_list if e.verdict == "PASS"),
        "fail": sum(1 for e in evidence_list if e.verdict != "PASS"),
        "verdict": "PASS" if all(e.verdict == "PASS" for e in evidence_list) else "FAIL",
    }

    # checklist
    checklist = build_readonly_transition_checklist()
    checklist_summary = summarize_readonly_transition_checklist(checklist)

    # notes
    notes: List[str] = []
    notes.extend(readiness.notes)
    notes.extend(blocker.notes)

    # resolve final status
    all_summaries = [
        manifest_summary,
        regression_summary,
        readiness_summary,
        blocker_summary,
        evidence_summary,
        checklist_summary,
    ]
    final_status = _resolve_final_status(all_summaries)

    return RuntimeGovernanceReadOnlyCloseoutBundle(
        manifest_summary=manifest_summary,
        regression_summary=regression_summary,
        readiness_summary=readiness_summary,
        blocker_summary=blocker_summary,
        evidence_summary=evidence_summary,
        checklist_summary=checklist_summary,
        final_status=final_status,
        notes=notes,
    )


# -- serialization --


def readonly_closeout_bundle_to_dict(
    bundle: RuntimeGovernanceReadOnlyCloseoutBundle,
) -> Dict[str, Any]:
    """Serialize bundle to a plain dict. Deterministic."""
    return {
        "manifest_summary": dict(bundle.manifest_summary),
        "regression_summary": dict(bundle.regression_summary),
        "readiness_summary": dict(bundle.readiness_summary),
        "blocker_summary": dict(bundle.blocker_summary),
        "evidence_summary": dict(bundle.evidence_summary),
        "checklist_summary": dict(bundle.checklist_summary),
        "final_status": bundle.final_status,
        "notes": list(bundle.notes),
    }


def readonly_closeout_bundle_to_markdown(
    bundle: RuntimeGovernanceReadOnlyCloseoutBundle,
) -> str:
    """Render bundle as deterministic markdown. No timestamps."""
    lines: List[str] = []

    lines.append("# Runtime Governance Read-Only Closeout Bundle")
    lines.append("")
    lines.append(f"**Final Status:** {bundle.final_status}")
    lines.append("")

    # manifest
    lines.append("## Stack Manifest")
    lines.append("")
    sm = bundle.manifest_summary
    lines.append(f"- **Total:** {sm.get('total', 'N/A')}")
    lines.append(f"- **Pass:** {sm.get('pass', 'N/A')}")
    lines.append(f"- **Fail:** {sm.get('fail', 'N/A')}")
    lines.append("")

    # regression
    lines.append("## Regression Packet")
    lines.append("")
    rg = bundle.regression_summary
    lines.append(f"- **Scenario Count:** {rg.get('scenario_count', 'N/A')}")
    lines.append(f"- **Pass:** {rg.get('scenario_pass_count', 'N/A')}")
    lines.append(f"- **Fail:** {rg.get('scenario_fail_count', 'N/A')}")
    lines.append(f"- **Final Verdict:** {rg.get('final_verdict', 'N/A')}")
    lines.append("")

    # readiness
    lines.append("## Readiness Score")
    lines.append("")
    rd = bundle.readiness_summary
    lines.append(f"- **Score:** {rd.get('score', 'N/A')}/{rd.get('max_score', 'N/A')}")
    lines.append(f"- **Percent:** {rd.get('percent', 'N/A')}%")
    lines.append(f"- **Grade:** {rd.get('grade', 'N/A')}")
    lines.append("")

    # blockers
    lines.append("## Blocker Summary")
    lines.append("")
    bk = bundle.blocker_summary
    lines.append(f"- **Total Blockers:** {bk.get('total_blockers', 'N/A')}")
    lines.append(f"- **Recommended Action:** {bk.get('recommended_action', 'N/A')}")
    lines.append("")

    # evidence
    lines.append("## Evidence Packet")
    lines.append("")
    ev = bundle.evidence_summary
    lines.append(f"- **Total:** {ev.get('total', 'N/A')}")
    lines.append(f"- **Pass:** {ev.get('pass', 'N/A')}")
    lines.append(f"- **Verdict:** {ev.get('verdict', 'N/A')}")
    lines.append("")

    # checklist
    lines.append("## Transition Checklist")
    lines.append("")
    cl = bundle.checklist_summary
    lines.append(f"- **Total:** {cl.get('total', 'N/A')}")
    lines.append(f"- **Required:** {cl.get('required', 'N/A')}")
    lines.append(f"- **Complete:** {cl.get('complete', 'N/A')}")
    lines.append(f"- **Pending:** {cl.get('pending', 'N/A')}")
    lines.append("")

    # notes
    if bundle.notes:
        lines.append("## Notes")
        lines.append("")
        for note in bundle.notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
