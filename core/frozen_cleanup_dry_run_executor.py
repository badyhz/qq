"""T17001 — Frozen Cleanup Dry-Run Executor.

Pure deterministic. No I/O. No network. No actual file operations.
Simulates cleanup actions without performing any real operation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_SIMULATED_OUTCOMES: tuple[str, ...] = (
    "SIMULATED_ARCHIVE",
    "SIMULATED_RETAIN",
    "SIMULATED_REVIEW",
    "SIMULATED_REJECT",
    "BLOCKED_NO_ACTION",
)

FORBIDDEN_OUTCOMES: tuple[str, ...] = (
    "ARCHIVED",
    "DELETED",
    "MOVED",
    "MODIFIED",
    "EXECUTED",
    "IMPORTED",
    "ACTIVATED",
)


@dataclass(frozen=True)
class CleanupDryRunResult:
    """Single cleanup dry-run execution result."""
    execution_id: str
    path: str
    decision: str
    simulated_outcome: str
    simulated_action_description: str
    preconditions_checked: list[str]
    preconditions_satisfied: bool
    would_copy: bool
    would_move: bool
    would_delete: bool
    would_modify: bool
    simulation_only: bool
    no_action_performed: bool
    human_approval_required: bool
    advisory_only: bool
    blocked_reason: str

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "path": self.path,
            "decision": self.decision,
            "simulated_outcome": self.simulated_outcome,
            "simulated_action_description": self.simulated_action_description,
            "preconditions_checked": self.preconditions_checked,
            "preconditions_satisfied": self.preconditions_satisfied,
            "would_copy": self.would_copy,
            "would_move": self.would_move,
            "would_delete": self.would_delete,
            "would_modify": self.would_modify,
            "simulation_only": self.simulation_only,
            "no_action_performed": self.no_action_performed,
            "human_approval_required": self.human_approval_required,
            "advisory_only": self.advisory_only,
            "blocked_reason": self.blocked_reason,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def _check_preconditions(decision_item: dict) -> tuple[list[str], bool, str]:
    """Check preconditions for a cleanup decision.

    Returns: (preconditions_list, all_satisfied, blocked_reason)
    """
    preconditions = [
        "release_hold_is_HOLD",
        "simulation_only_enforced",
        "no_real_file_operations",
        "human_approval_obtained",
        "evidence_sufficient",
        "blocker_cleared",
    ]

    preconds_met = decision_item.get("preconditions_met", False)
    evidence = decision_item.get("evidence_sufficient", False)
    approval = decision_item.get("approval_obtained", False)
    blocker = decision_item.get("blocker_cleared", False)

    satisfied = preconds_met and evidence and approval and blocker
    blocked = ""
    if not satisfied:
        reasons = []
        if not preconds_met:
            reasons.append("preconditions_not_met")
        if not evidence:
            reasons.append("evidence_insufficient")
        if not approval:
            reasons.append("approval_not_obtained")
        if not blocker:
            reasons.append("blocker_not_cleared")
        blocked = "; ".join(reasons)

    return preconditions, satisfied, blocked


def _simulate_decision(decision: str, satisfied: bool) -> tuple[str, str]:
    """Map a decision to a simulated outcome and description."""
    if not satisfied:
        return "BLOCKED_NO_ACTION", "preconditions_not_satisfied_no_action_simulated"

    mapping = {
        "ARCHIVE_PROPOSED": (
            "SIMULATED_ARCHIVE",
            "would_archive_to_simulated_path_after_human_approval",
        ),
        "RETAIN_FROZEN": (
            "SIMULATED_RETAIN",
            "would_retain_as_frozen_no_change",
        ),
        "REVIEW_REQUIRED": (
            "SIMULATED_REVIEW",
            "would_await_human_review_before_any_decision",
        ),
        "REJECT_FROM_CLEANUP": (
            "SIMULATED_REJECT",
            "would_reject_from_cleanup_process",
        ),
    }
    return mapping.get(decision, ("BLOCKED_NO_ACTION", "unknown_decision"))


def execute_dry_run(decision_item: dict) -> CleanupDryRunResult:
    """Execute a single cleanup dry-run for a decision item."""
    path = decision_item.get("path", "unknown")
    safe_id = _safe_id(path)
    decision = decision_item.get("decision", "UNKNOWN")

    preconds, satisfied, blocked = _check_preconditions(decision_item)
    outcome, description = _simulate_decision(decision, satisfied)

    return CleanupDryRunResult(
        execution_id=f"dryrun_{safe_id}",
        path=path,
        decision=decision,
        simulated_outcome=outcome,
        simulated_action_description=description,
        preconditions_checked=preconds,
        preconditions_satisfied=satisfied,
        would_copy=False,
        would_move=False,
        would_delete=False,
        would_modify=False,
        simulation_only=True,
        no_action_performed=True,
        human_approval_required=True,
        advisory_only=True,
        blocked_reason=blocked,
    )


def execute_cleanup_dry_run(
    decision_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[CleanupDryRunResult]:
    """Execute dry-run for all cleanup decisions."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    return [execute_dry_run(di) for di in decision_items]


def compute_dry_run_hash(items: list[CleanupDryRunResult]) -> str:
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_dry_run_markdown(items: list[CleanupDryRunResult]) -> str:
    lines = [
        "# Frozen Cleanup Dry-Run Report",
        "",
        f"**Total items:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**simulation_only:** true for all items",
        f"**no_action_performed:** true for all items",
        "",
        "## Safety Boundary",
        "",
        "- would_copy: **false** for all items",
        "- would_move: **false** for all items",
        "- would_delete: **false** for all items",
        "- would_modify: **false** for all items",
        "- simulation_only: **true** for all items",
        "- no_action_performed: **true** for all items",
        "- human_approval_required: **true** for all items",
        "- advisory_only: **true** for all items",
        "",
        "## Outcome Summary",
        "",
    ]

    outcome_counts: dict[str, int] = {}
    for item in items:
        outcome_counts[item.simulated_outcome] = outcome_counts.get(item.simulated_outcome, 0) + 1
    for outcome, count in sorted(outcome_counts.items()):
        lines.append(f"- **{outcome}:** {count}")

    lines.append("")
    lines.append("## Precondition Summary")
    lines.append("")

    satisfied_count = sum(1 for i in items if i.preconditions_satisfied)
    blocked_count = len(items) - satisfied_count
    lines.append(f"- **Preconditions satisfied:** {satisfied_count}")
    lines.append(f"- **Blocked:** {blocked_count}")

    lines.append("")
    lines.append("## Dry-Run Results")
    lines.append("")

    for item in items:
        lines.append(f"### {item.path}")
        lines.append("")
        lines.append(f"- **execution_id:** {item.execution_id}")
        lines.append(f"- **decision:** {item.decision}")
        lines.append(f"- **simulated_outcome:** {item.simulated_outcome}")
        lines.append(f"- **simulated_action_description:** {item.simulated_action_description}")
        lines.append(f"- **preconditions_satisfied:** {item.preconditions_satisfied}")
        lines.append(f"- **blocked_reason:** {item.blocked_reason or 'none'}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def write_json(items: list[CleanupDryRunResult], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(
    items: list[CleanupDryRunResult],
    out_path,
    release_hold: str,
) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    outcome_counts: dict[str, int] = {}
    for item in items:
        outcome_counts[item.simulated_outcome] = outcome_counts.get(item.simulated_outcome, 0) + 1
    manifest = {
        "total_items": len(items),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "release_hold": release_hold,
        "simulation_only": True,
        "no_action_performed": True,
        "would_copy": False,
        "would_move": False,
        "would_delete": False,
        "would_modify": False,
        "human_approval_required": True,
        "advisory_only": True,
        "dry_run_hash": compute_dry_run_hash(items),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[CleanupDryRunResult], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_dry_run_markdown(items), encoding="utf-8")
