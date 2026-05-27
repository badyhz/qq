"""Read-only hook invariants — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

INVARIANT_IDS = ["no_mutation", "no_network", "no_secrets", "no_live_paths", "no_planner"]


@dataclass(frozen=True)
class InvariantResult:
    invariant_id: str
    passed: bool
    message: str


@dataclass(frozen=True)
class InvariantCheckResult:
    results: List[InvariantResult]
    all_passed: bool
    failed_count: int


def check_invariants(hook_input) -> InvariantCheckResult:
    """Check invariants against a ReadOnlyHookInput. Pure logic, no I/O."""
    results: List[InvariantResult] = []

    # no_mutation: operation_kind must not be a mutation type
    mutation_ops = {"mutate", "write", "delete", "submit"}
    if hook_input.operation_kind in mutation_ops:
        results.append(InvariantResult("no_mutation", False, f"Operation {hook_input.operation_kind!r} is a mutation"))
    else:
        results.append(InvariantResult("no_mutation", True, "No mutation detected"))

    # no_network: context must not contain network indicators
    network_keys = {"url", "endpoint", "host", "ip", "socket"}
    context_keys = {k.lower() for k in hook_input.context}
    net_violations = context_keys & network_keys
    if net_violations:
        results.append(InvariantResult("no_network", False, f"Network keys found: {net_violations}"))
    else:
        results.append(InvariantResult("no_network", True, "No network indicators"))

    # no_secrets: payload must not contain secret patterns
    from core.read_only_hook_sanitizer import SECRET_PATTERNS

    secret_keys = {
        k for k in hook_input.payload
        if any(p in k.lower() for p in SECRET_PATTERNS)
    }
    if secret_keys:
        results.append(InvariantResult("no_secrets", False, f"Secret keys found: {secret_keys}"))
    else:
        results.append(InvariantResult("no_secrets", True, "No secrets detected"))

    # no_live_paths: permission_flags must not include live/execute flags
    live_flags = {"live", "execute", "real", "production"}
    flagged = {f for f in hook_input.permission_flags if f.lower() in live_flags}
    if flagged:
        results.append(InvariantResult("no_live_paths", False, f"Live flags found: {flagged}"))
    else:
        results.append(InvariantResult("no_live_paths", True, "No live paths"))

    # no_planner: context must not reference planner/agent execution
    planner_keys = {"planner", "agent_run", "scheduler", "orchestrator"}
    planner_violations = context_keys & planner_keys
    if planner_violations:
        results.append(InvariantResult("no_planner", False, f"Planner keys found: {planner_violations}"))
    else:
        results.append(InvariantResult("no_planner", True, "No planner references"))

    failed = [r for r in results if not r.passed]
    return InvariantCheckResult(
        results=results,
        all_passed=len(failed) == 0,
        failed_count=len(failed),
    )


def invariant_result_to_dict(ir: InvariantResult) -> dict:
    return {
        "invariant_id": ir.invariant_id,
        "passed": ir.passed,
        "message": ir.message,
    }


def invariant_check_result_to_dict(icr: InvariantCheckResult) -> dict:
    return {
        "results": [invariant_result_to_dict(r) for r in icr.results],
        "all_passed": icr.all_passed,
        "failed_count": icr.failed_count,
    }
