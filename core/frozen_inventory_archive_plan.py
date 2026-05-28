"""Frozen inventory archive plan — no-touch migration design.

Consumes decision_matrix.json and produces future proposed actions only.
Never moves, deletes, renames, modifies, stages, or executes any file.

release_hold = HOLD
advisory_only = True
no_live / no_submit / no_exchange / no_network = True
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

RELEASE_HOLD_REQUIRED = "HOLD"

# Disposition -> proposed future action mapping
DISPOSITION_ACTION_MAP = {
    "KEEP_FROZEN": "NO_ACTION",
    "NEEDS_HUMAN_REVIEW": "AWAIT_HUMAN_DECISION",
    "CANDIDATE_FOR_ARCHIVE": "MOVE_TO_ARCHIVE_AFTER_APPROVAL",
    "CANDIDATE_FOR_REWRITE": "REWRITE_FROM_SCRATCH_AFTER_APPROVAL",
    "CANDIDATE_FOR_DELETION_AFTER_BACKUP": "BACKUP_THEN_DELETE_AFTER_APPROVAL",
    "UNKNOWN": "AWAIT_HUMAN_DECISION",
}

# Actions that are forbidden (never proposed)
FORBIDDEN_ACTIONS = ["EXECUTE", "IMPORT", "STAGE", "ACTIVATE", "SUBMIT"]


@dataclass
class ArchivePlanEntry:
    path: str
    current_disposition: str
    proposed_future_action: str
    requires_backup: bool
    requires_human_approval: bool
    required_preconditions: list[str] = field(default_factory=list)
    forbidden_until_approved: list[str] = field(default_factory=list)
    rollback_note: str = ""
    no_touch_confirmed: bool = True


@dataclass
class ArchivePlan:
    entries: list[ArchivePlanEntry]
    manifest: dict[str, Any]
    keep_frozen: list[str] = field(default_factory=list)
    human_review_queue: list[str] = field(default_factory=list)
    archive_candidates: list[str] = field(default_factory=list)
    rewrite_candidates: list[str] = field(default_factory=list)
    delete_after_backup_candidates: list[str] = field(default_factory=list)
    unknown_review_required: list[str] = field(default_factory=list)


def _build_preconditions(disposition: str) -> list[str]:
    if disposition == "KEEP_FROZEN":
        return ["No preconditions — remain frozen"]
    if disposition == "NEEDS_HUMAN_REVIEW":
        return ["Human must inspect and decide disposition"]
    if disposition == "CANDIDATE_FOR_ARCHIVE":
        return [
            "Human must approve archive target",
            "Verify no live dependencies",
            "Create backup before moving",
        ]
    if disposition == "CANDIDATE_FOR_REWRITE":
        return [
            "Human must approve rewrite scope",
            "Original must be backed up",
            "Rewritten version must pass review",
        ]
    if disposition == "CANDIDATE_FOR_DELETION_AFTER_BACKUP":
        return [
            "Backup must be verified",
            "Human must approve deletion",
            "Backup integrity check required",
        ]
    if disposition == "UNKNOWN":
        return ["Full human inspection required"]
    return ["Human must review"]


def _build_forbidden(disposition: str) -> list[str]:
    base = ["execute", "import", "stage"]
    if disposition in ("CANDIDATE_FOR_ARCHIVE", "CANDIDATE_FOR_DELETION_AFTER_BACKUP"):
        base.extend(["move", "delete", "rename"])
    if disposition == "CANDIDATE_FOR_REWRITE":
        base.extend(["modify", "overwrite"])
    return base


def _build_rollback(disposition: str) -> str:
    if disposition == "KEEP_FROZEN":
        return "No rollback needed — no action taken"
    if disposition == "NEEDS_HUMAN_REVIEW":
        return "No action taken — no rollback needed"
    if disposition == "CANDIDATE_FOR_ARCHIVE":
        return "Restore from backup to original location"
    if disposition == "CANDIDATE_FOR_REWRITE":
        return "Restore original from backup"
    if disposition == "CANDIDATE_FOR_DELETION_AFTER_BACKUP":
        return "Restore from verified backup"
    if disposition == "UNKNOWN":
        return "No action taken — no rollback needed"
    return "Restore from backup"


def build_archive_plan(matrix_data: dict[str, Any]) -> ArchivePlan:
    """Build archive plan from decision matrix JSON data."""
    entries: list[ArchivePlanEntry] = []
    keep_frozen: list[str] = []
    human_review_queue: list[str] = []
    archive_candidates: list[str] = []
    rewrite_candidates: list[str] = []
    delete_after_backup_candidates: list[str] = []
    unknown_review_required: list[str] = []

    for entry_data in matrix_data.get("entries", []):
        path = entry_data.get("path", "")
        disposition = entry_data.get("disposition", "UNKNOWN")

        proposed_action = DISPOSITION_ACTION_MAP.get(disposition, "AWAIT_HUMAN_DECISION")
        requires_backup = disposition in (
            "CANDIDATE_FOR_ARCHIVE",
            "CANDIDATE_FOR_REWRITE",
            "CANDIDATE_FOR_DELETION_AFTER_BACKUP",
        )
        requires_human = disposition != "KEEP_FROZEN"
        preconditions = _build_preconditions(disposition)
        forbidden = _build_forbidden(disposition)
        rollback = _build_rollback(disposition)

        entry = ArchivePlanEntry(
            path=path,
            current_disposition=disposition,
            proposed_future_action=proposed_action,
            requires_backup=requires_backup,
            requires_human_approval=requires_human,
            required_preconditions=preconditions,
            forbidden_until_approved=forbidden,
            rollback_note=rollback,
            no_touch_confirmed=True,
        )
        entries.append(entry)

        # Categorize
        if disposition == "KEEP_FROZEN":
            keep_frozen.append(path)
        elif disposition == "NEEDS_HUMAN_REVIEW":
            human_review_queue.append(path)
        elif disposition == "CANDIDATE_FOR_ARCHIVE":
            archive_candidates.append(path)
        elif disposition == "CANDIDATE_FOR_REWRITE":
            rewrite_candidates.append(path)
        elif disposition == "CANDIDATE_FOR_DELETION_AFTER_BACKUP":
            delete_after_backup_candidates.append(path)
        else:
            unknown_review_required.append(path)

    manifest = _build_manifest(entries)
    plan = ArchivePlan(
        entries=entries,
        manifest=manifest,
        keep_frozen=keep_frozen,
        human_review_queue=human_review_queue,
        archive_candidates=archive_candidates,
        rewrite_candidates=rewrite_candidates,
        delete_after_backup_candidates=delete_after_backup_candidates,
        unknown_review_required=unknown_review_required,
    )
    return plan


def _build_manifest(entries: list[ArchivePlanEntry]) -> dict[str, Any]:
    action_counts: dict[str, int] = {}
    for e in entries:
        action_counts[e.proposed_future_action] = action_counts.get(e.proposed_future_action, 0) + 1

    return {
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_execution": True,
        "no_import": True,
        "no_stage": True,
        "no_actual_move": True,
        "no_actual_delete": True,
        "no_actual_rename": True,
        "no_actual_modify": True,
        "no_touch_plan_only": True,
        "generated_by": "frozen_inventory_archive_plan.py",
        "total_entries": len(entries),
        "action_counts": action_counts,
    }


def validate_no_forbidden_actions(plan: ArchivePlan) -> list[str]:
    """Check that no proposed action is in the forbidden list."""
    violations: list[str] = []
    for entry in plan.entries:
        if entry.proposed_future_action in FORBIDDEN_ACTIONS:
            violations.append(f"{entry.path}: proposed action {entry.proposed_future_action}")
    return violations


def validate_no_touch(plan: ArchivePlan) -> list[str]:
    """Check that all entries have no_touch_confirmed=True."""
    violations: list[str] = []
    for entry in plan.entries:
        if not entry.no_touch_confirmed:
            violations.append(f"{entry.path}: no_touch_confirmed is False")
    return violations


def validate_release_hold(plan: ArchivePlan, release_hold: str) -> bool:
    return release_hold == RELEASE_HOLD_REQUIRED


def write_json(plan: ArchivePlan, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "manifest": plan.manifest,
        "keep_frozen": plan.keep_frozen,
        "human_review_queue": plan.human_review_queue,
        "archive_candidates": plan.archive_candidates,
        "rewrite_candidates": plan.rewrite_candidates,
        "delete_after_backup_candidates": plan.delete_after_backup_candidates,
        "unknown_review_required": plan.unknown_review_required,
        "entries": [_entry_to_dict(e) for e in plan.entries],
    }
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(plan: ArchivePlan, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(plan: ArchivePlan, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Frozen Inventory Archive Plan")
    lines.append("")
    lines.append(f"**release_hold:** {plan.manifest['release_hold']}")
    lines.append(f"**advisory_only:** {plan.manifest['advisory_only']}")
    lines.append(f"**no_touch_plan_only:** {plan.manifest['no_touch_plan_only']}")
    lines.append(f"**total entries:** {len(plan.entries)}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Keep Frozen: {len(plan.keep_frozen)}")
    lines.append(f"- Human Review Queue: {len(plan.human_review_queue)}")
    lines.append(f"- Archive Candidates: {len(plan.archive_candidates)}")
    lines.append(f"- Rewrite Candidates: {len(plan.rewrite_candidates)}")
    lines.append(f"- Delete After Backup: {len(plan.delete_after_backup_candidates)}")
    lines.append(f"- Unknown Review Required: {len(plan.unknown_review_required)}")
    lines.append("")

    lines.append("## Proposed Actions")
    lines.append("")
    lines.append("| Path | Disposition | Proposed Action | Backup | Human Approval |")
    lines.append("|------|-------------|-----------------|--------|----------------|")
    for e in plan.entries:
        backup = "Yes" if e.requires_backup else "No"
        human = "Yes" if e.requires_human_approval else "No"
        lines.append(f"| {e.path} | {e.current_disposition} | {e.proposed_future_action} | {backup} | {human} |")
    lines.append("")

    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No actual file moves")
    lines.append("- No actual file deletes")
    lines.append("- No actual file renames")
    lines.append("- No actual file modifications")
    lines.append("- Plan-only. No-touch confirmed.")
    lines.append("- release_hold = HOLD")
    lines.append("- Advisory only. Human review required.")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _entry_to_dict(entry: ArchivePlanEntry) -> dict[str, Any]:
    return {
        "path": entry.path,
        "current_disposition": entry.current_disposition,
        "proposed_future_action": entry.proposed_future_action,
        "requires_backup": entry.requires_backup,
        "requires_human_approval": entry.requires_human_approval,
        "required_preconditions": entry.required_preconditions,
        "forbidden_until_approved": entry.forbidden_until_approved,
        "rollback_note": entry.rollback_note,
        "no_touch_confirmed": entry.no_touch_confirmed,
    }
