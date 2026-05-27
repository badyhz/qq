"""Read-only hook contract — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ReadOnlyHookInput:
    hook_id: str
    operation_kind: str  # "query", "validate", "inspect", "report"
    payload: Dict[str, Any]
    permission_flags: List[str]
    context: Dict[str, Any]


@dataclass(frozen=True)
class ReadOnlyHookOutput:
    hook_id: str
    result_status: str  # "success", "denied", "error"
    sanitized_output: Dict[str, Any]
    evidence_record_id: str
    invariant_results: List[str]
    side_effects_declared: List[str]  # must be empty for read-only


VALID_OPERATION_KINDS = frozenset({"query", "validate", "inspect", "report"})
VALID_RESULT_STATUSES = frozenset({"success", "denied", "error"})


def build_read_only_hook_input(
    hook_id: str,
    operation_kind: str,
    payload: Dict[str, Any],
    permission_flags: List[str],
    context: Dict[str, Any],
) -> ReadOnlyHookInput:
    if operation_kind not in VALID_OPERATION_KINDS:
        raise ValueError(f"Invalid operation_kind: {operation_kind!r}")
    return ReadOnlyHookInput(
        hook_id=hook_id,
        operation_kind=operation_kind,
        payload=dict(payload),
        permission_flags=list(permission_flags),
        context=dict(context),
    )


def build_read_only_hook_output(
    hook_id: str,
    result_status: str,
    sanitized_output: Dict[str, Any],
    evidence_record_id: str,
    invariant_results: List[str],
    side_effects_declared: List[str],
) -> ReadOnlyHookOutput:
    if result_status not in VALID_RESULT_STATUSES:
        raise ValueError(f"Invalid result_status: {result_status!r}")
    if side_effects_declared:
        raise ValueError("Read-only hook must have empty side_effects_declared")
    return ReadOnlyHookOutput(
        hook_id=hook_id,
        result_status=result_status,
        sanitized_output=dict(sanitized_output),
        evidence_record_id=evidence_record_id,
        invariant_results=list(invariant_results),
        side_effects_declared=list(side_effects_declared),
    )


def hook_input_to_dict(inp: ReadOnlyHookInput) -> dict:
    return {
        "hook_id": inp.hook_id,
        "operation_kind": inp.operation_kind,
        "payload": dict(inp.payload),
        "permission_flags": list(inp.permission_flags),
        "context": dict(inp.context),
    }


def hook_output_to_dict(out: ReadOnlyHookOutput) -> dict:
    return {
        "hook_id": out.hook_id,
        "result_status": out.result_status,
        "sanitized_output": dict(out.sanitized_output),
        "evidence_record_id": out.evidence_record_id,
        "invariant_results": list(out.invariant_results),
        "side_effects_declared": list(out.side_effects_declared),
    }
