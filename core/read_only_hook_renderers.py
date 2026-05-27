"""Read-only hook renderers — deterministic markdown output, no I/O, no timestamps."""
from __future__ import annotations

from typing import Any, Dict, List

from core.read_only_hook_contract import ReadOnlyHookInput, ReadOnlyHookOutput
from core.read_only_hook_permissions import ReadOnlyPermission
from core.read_only_hook_sanitizer import SanitizedPayload
from core.read_only_hook_invariants import InvariantCheckResult, InvariantResult
from core.read_only_hook_failures import HookFailure
from core.read_only_hook_evidence import EvidenceRecord
from core.read_only_hook_regression_matrix import RegressionTestCase
from core.read_only_hook_review import ReviewChecklist, ReviewChecklistItem
from core.read_only_hook_rollout import RolloutHold, RollbackStep
from core.read_only_hook_observability import ObservabilityEvent
from core.read_only_hook_threat_model import ThreatModelItem
from core.read_only_hook_boundary_map import BoundaryEntry
from core.read_only_hook_prompt_pack import ReadOnlyHookPromptPack


def render_hook_input_markdown(input: ReadOnlyHookInput) -> str:
    flags = sorted(input.permission_flags)
    payload_keys = sorted(input.payload.keys())
    context_keys = sorted(input.context.keys())
    lines = [
        "# Hook Input",
        "",
        f"- **hook_id**: {input.hook_id}",
        f"- **operation_kind**: {input.operation_kind}",
        f"- **permission_flags**: {', '.join(flags)}",
        "",
        "## Payload Keys",
        "",
    ]
    for k in payload_keys:
        lines.append(f"- {k}")
    lines.append("")
    lines.append("## Context Keys")
    lines.append("")
    for k in context_keys:
        lines.append(f"- {k}")
    return "\n".join(lines) + "\n"


def render_hook_output_markdown(output: ReadOnlyHookOutput) -> str:
    invariants = sorted(output.invariant_results)
    side_effects = sorted(output.side_effects_declared)
    out_keys = sorted(output.sanitized_output.keys())
    lines = [
        "# Hook Output",
        "",
        f"- **hook_id**: {output.hook_id}",
        f"- **result_status**: {output.result_status}",
        f"- **evidence_record_id**: {output.evidence_record_id}",
        "",
        "## Invariant Results",
        "",
    ]
    for inv in invariants:
        lines.append(f"- {inv}")
    lines.append("")
    lines.append("## Side Effects Declared")
    lines.append("")
    if side_effects:
        for se in side_effects:
            lines.append(f"- {se}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Sanitized Output Keys")
    lines.append("")
    for k in out_keys:
        lines.append(f"- {k}")
    return "\n".join(lines) + "\n"


def render_permission_audit_markdown(permissions: List[ReadOnlyPermission]) -> str:
    sorted_perms = sorted(permissions, key=lambda p: p.name)
    lines = [
        "# Permission Audit",
        "",
        "| Permission | Granted | Denial Reason |",
        "|---|---|---|",
    ]
    for p in sorted_perms:
        granted = "yes" if p.granted else "no"
        reason = p.denial_reason if p.denial_reason else "-"
        lines.append(f"| {p.name} | {granted} | {reason} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_sanitized_payload_markdown(sanitized: SanitizedPayload) -> str:
    lines = [
        "# Sanitized Payload",
        "",
        f"- **original_keys**: {', '.join(sanitized.original_keys)}",
        f"- **sanitized_keys**: {', '.join(sanitized.sanitized_keys)}",
        "",
        "## Redacted Fields",
        "",
    ]
    if sanitized.redacted_fields:
        for f in sanitized.redacted_fields:
            lines.append(f"- {f}")
    else:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


def render_invariant_packet_markdown(result: InvariantCheckResult) -> str:
    lines = [
        "# Invariant Check Result",
        "",
        f"- **all_passed**: {result.all_passed}",
        f"- **failed_count**: {result.failed_count}",
        "",
        "| Invariant | Passed | Message |",
        "|---|---|---|",
    ]
    for r in result.results:
        passed = "PASS" if r.passed else "FAIL"
        lines.append(f"| {r.invariant_id} | {passed} | {r.message} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_failure_taxonomy_markdown(failures: List[HookFailure]) -> str:
    sorted_fails = sorted(failures, key=lambda f: (f.category, f.failure_id))
    lines = [
        "# Failure Taxonomy",
        "",
        "| Failure ID | Category | Task | Recoverable | Message |",
        "|---|---|---|---|---|",
    ]
    for f in sorted_fails:
        rec = "yes" if f.recoverable else "no"
        lines.append(f"| {f.failure_id} | {f.category} | {f.task_id} | {rec} | {f.message} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_evidence_packet_markdown(evidence: EvidenceRecord) -> str:
    checked = sorted(evidence.invariants_checked)
    passed = sorted(evidence.invariants_passed)
    notes = list(evidence.notes)
    lines = [
        "# Evidence Packet",
        "",
        f"- **evidence_id**: {evidence.evidence_id}",
        f"- **hook_id**: {evidence.hook_id}",
        f"- **operation**: {evidence.operation}",
        f"- **result_status**: {evidence.result_status}",
        "",
        "## Invariants Checked",
        "",
    ]
    for inv in checked:
        lines.append(f"- {inv}")
    lines.append("")
    lines.append("## Invariants Passed")
    lines.append("")
    for inv in passed:
        lines.append(f"- {inv}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for n in notes:
        lines.append(f"- {n}")
    return "\n".join(lines) + "\n"


def render_regression_matrix_markdown(cases: List[RegressionTestCase]) -> str:
    sorted_cases = sorted(cases, key=lambda c: c.test_id)
    lines = [
        "# Regression Matrix",
        "",
        "| Test ID | Description | Expected Status | Category |",
        "|---|---|---|---|",
    ]
    for c in sorted_cases:
        lines.append(f"| {c.test_id} | {c.description} | {c.expected_status} | {c.category} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_review_checklist_markdown(checklist: ReviewChecklist) -> str:
    items = sorted(checklist.items, key=lambda i: i.item_id)
    lines = [
        "# Review Checklist",
        "",
        f"- **checklist_id**: {checklist.checklist_id}",
        f"- **all_checked**: {checklist.all_checked}",
        f"- **verdict**: {checklist.verdict}",
        "",
        "| Item ID | Description | Checked | Notes |",
        "|---|---|---|---|",
    ]
    for item in items:
        checked = "x" if item.checked else " "
        notes = item.notes if item.notes else "-"
        lines.append(f"| {item.item_id} | {item.description} | [{checked}] | {notes} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_rollout_hold_markdown(hold: RolloutHold) -> str:
    reasons = list(hold.reasons)
    conditions = list(hold.release_conditions)
    lines = [
        "# Rollout Hold",
        "",
        f"- **hold_id**: {hold.hold_id}",
        f"- **hold_active**: {hold.hold_active}",
        f"- **scope**: {hold.scope}",
        f"- **final_verdict**: {hold.final_verdict}",
        "",
        "## Reasons",
        "",
    ]
    for r in reasons:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("## Release Conditions")
    lines.append("")
    for c in conditions:
        lines.append(f"- {c}")
    return "\n".join(lines) + "\n"


def render_rollback_plan_markdown(steps: List[RollbackStep]) -> str:
    sorted_steps = sorted(steps, key=lambda s: s.order)
    lines = [
        "# Rollback Plan",
        "",
        "| Step | Order | Description | Reversible |",
        "|---|---|---|---|",
    ]
    for s in sorted_steps:
        rev = "yes" if s.reversible else "no"
        lines.append(f"| {s.step_id} | {s.order} | {s.description} | {rev} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_observability_packet_markdown(events: List[ObservabilityEvent]) -> str:
    sorted_events = sorted(events, key=lambda e: e.event_id)
    lines = [
        "# Observability Packet",
        "",
        "| Event ID | Observation Point | Hook ID | Status |",
        "|---|---|---|---|",
    ]
    for e in sorted_events:
        lines.append(f"| {e.event_id} | {e.observation_point} | {e.hook_id} | {e.status} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_threat_model_markdown(threats: List[ThreatModelItem]) -> str:
    sorted_threats = sorted(threats, key=lambda t: t.threat_id)
    lines = [
        "# Threat Model",
        "",
        "| Threat ID | Title | Severity | Status | Mitigation |",
        "|---|---|---|---|---|",
    ]
    for t in sorted_threats:
        lines.append(
            f"| {t.threat_id} | {t.title} | {t.severity} | {t.status} | {t.mitigation} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def render_boundary_map_markdown(boundaries: List[BoundaryEntry]) -> str:
    sorted_boundaries = sorted(boundaries, key=lambda b: b.component)
    lines = [
        "# Boundary Map",
        "",
        "| Component | Access Level | Reason |",
        "|---|---|---|",
    ]
    for b in sorted_boundaries:
        lines.append(f"| {b.component} | {b.access_level} | {b.reason} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_prompt_pack_markdown(pack: ReadOnlyHookPromptPack) -> str:
    docs = list(pack.required_docs)
    warnings = list(pack.safety_warnings)
    lines = [
        "# Prompt Pack",
        "",
        f"- **pack_id**: {pack.pack_id}",
        f"- **task_range**: {pack.task_range}",
        "",
        "## Prompt Text",
        "",
        pack.prompt_text,
        "",
        "## Required Docs",
        "",
    ]
    for d in docs:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("## Safety Warnings")
    lines.append("")
    for w in warnings:
        lines.append(f"- {w}")
    lines.append("")
    lines.append("## Hard Stop")
    lines.append("")
    lines.append(pack.hard_stop)
    return "\n".join(lines) + "\n"


def render_acceptance_summary_markdown(verdict: str, notes: List[str]) -> str:
    lines = [
        "# Acceptance Summary",
        "",
        f"- **verdict**: {verdict}",
        "",
        "## Notes",
        "",
    ]
    for n in notes:
        lines.append(f"- {n}")
    return "\n".join(lines) + "\n"


def render_final_status_markdown(status: str, task_range: str, notes: List[str]) -> str:
    lines = [
        "# Final Status",
        "",
        f"- **status**: {status}",
        f"- **task_range**: {task_range}",
        "",
        "## Notes",
        "",
    ]
    for n in notes:
        lines.append(f"- {n}")
    return "\n".join(lines) + "\n"
