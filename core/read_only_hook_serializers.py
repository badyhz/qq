"""Read-only hook serializers — stable dicts with sorted keys, no I/O, no timestamps."""
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


def serialize_hook_input(input: ReadOnlyHookInput) -> dict:
    return {
        "context": dict(input.context),
        "hook_id": input.hook_id,
        "operation_kind": input.operation_kind,
        "payload": dict(input.payload),
        "permission_flags": sorted(input.permission_flags),
    }


def serialize_hook_output(output: ReadOnlyHookOutput) -> dict:
    return {
        "evidence_record_id": output.evidence_record_id,
        "hook_id": output.hook_id,
        "invariant_results": sorted(output.invariant_results),
        "result_status": output.result_status,
        "sanitized_output": dict(output.sanitized_output),
        "side_effects_declared": sorted(output.side_effects_declared),
    }


def serialize_permission(permission: ReadOnlyPermission) -> dict:
    return {
        "denial_reason": permission.denial_reason,
        "granted": permission.granted,
        "name": permission.name,
        "permission_id": permission.permission_id,
    }


def serialize_sanitized_payload(payload: SanitizedPayload) -> dict:
    return {
        "original_keys": sorted(payload.original_keys),
        "payload": dict(payload.payload),
        "redacted_fields": sorted(payload.redacted_fields),
        "sanitized_keys": sorted(payload.sanitized_keys),
    }


def serialize_invariant_result(result: InvariantResult) -> dict:
    return {
        "invariant_id": result.invariant_id,
        "message": result.message,
        "passed": result.passed,
    }


def serialize_invariant_check_result(result: InvariantCheckResult) -> dict:
    return {
        "all_passed": result.all_passed,
        "failed_count": result.failed_count,
        "results": [serialize_invariant_result(r) for r in result.results],
    }


def serialize_failure(failure: HookFailure) -> dict:
    return {
        "category": failure.category,
        "failure_id": failure.failure_id,
        "message": failure.message,
        "recoverable": failure.recoverable,
        "task_id": failure.task_id,
    }


def serialize_evidence(evidence: EvidenceRecord) -> dict:
    return {
        "evidence_id": evidence.evidence_id,
        "hook_id": evidence.hook_id,
        "invariants_checked": sorted(evidence.invariants_checked),
        "invariants_passed": sorted(evidence.invariants_passed),
        "notes": list(evidence.notes),
        "operation": evidence.operation,
        "result_status": evidence.result_status,
    }


def serialize_regression_case(case: RegressionTestCase) -> dict:
    return {
        "category": case.category,
        "description": case.description,
        "expected_status": case.expected_status,
        "test_id": case.test_id,
    }


def _serialize_review_checklist_item(item: ReviewChecklistItem) -> dict:
    return {
        "checked": item.checked,
        "description": item.description,
        "item_id": item.item_id,
        "notes": item.notes,
    }


def serialize_review_checklist(checklist: ReviewChecklist) -> dict:
    return {
        "all_checked": checklist.all_checked,
        "checklist_id": checklist.checklist_id,
        "items": [_serialize_review_checklist_item(i) for i in checklist.items],
        "verdict": checklist.verdict,
    }


def serialize_rollout_hold(hold: RolloutHold) -> dict:
    return {
        "final_verdict": hold.final_verdict,
        "hold_active": hold.hold_active,
        "hold_id": hold.hold_id,
        "reasons": list(hold.reasons),
        "release_conditions": list(hold.release_conditions),
        "scope": hold.scope,
    }


def serialize_rollback_step(step: RollbackStep) -> dict:
    return {
        "description": step.description,
        "order": step.order,
        "reversible": step.reversible,
        "step_id": step.step_id,
    }


def serialize_observability_event(event: ObservabilityEvent) -> dict:
    return {
        "details": dict(event.details),
        "event_id": event.event_id,
        "hook_id": event.hook_id,
        "observation_point": event.observation_point,
        "status": event.status,
    }


def serialize_threat_item(item: ThreatModelItem) -> dict:
    return {
        "mitigation": item.mitigation,
        "severity": item.severity,
        "status": item.status,
        "threat_id": item.threat_id,
        "title": item.title,
    }


def serialize_boundary_entry(entry: BoundaryEntry) -> dict:
    return {
        "access_level": entry.access_level,
        "component": entry.component,
        "reason": entry.reason,
    }


def serialize_prompt_pack(pack: ReadOnlyHookPromptPack) -> dict:
    return {
        "hard_stop": pack.hard_stop,
        "pack_id": pack.pack_id,
        "prompt_text": pack.prompt_text,
        "required_docs": list(pack.required_docs),
        "safety_warnings": list(pack.safety_warnings),
        "task_range": pack.task_range,
    }
