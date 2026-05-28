"""T15001 — Frozen Archive/Delete Decision Prep builder.

Pure deterministic. No I/O. No network. No file operations.
Reads human review queue, produces decision prep items.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

CANDIDATE_ACTIONS: tuple[str, ...] = (
    "KEEP_FROZEN",
    "PREPARE_ARCHIVE_AFTER_BACKUP",
    "PREPARE_DELETE_AFTER_BACKUP",
    "PREPARE_OFFLINE_REWRITE",
    "NEEDS_MORE_REVIEW",
)

FORBIDDEN_IMMEDIATE_ACTIONS: tuple[str, ...] = (
    "DELETE_NOW",
    "MOVE_NOW",
    "EXECUTE_NOW",
    "IMPORT_NOW",
    "ACTIVATE_NOW",
)


@dataclass(frozen=True)
class DecisionPrepItem:
    """Single archive/delete decision prep entry."""
    path: str
    priority: str
    current_disposition: str
    candidate_action: str
    backup_required: bool
    backup_method: str
    deletion_allowed_now: bool
    archive_allowed_now: bool
    rewrite_allowed_now: bool
    required_human_approval: bool
    required_backup_evidence: list[str]
    required_diff_review: bool
    required_owner_note: bool
    rollback_plan: str
    final_manual_decision_placeholder: str
    no_touch_until_approved: bool

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "priority": self.priority,
            "current_disposition": self.current_disposition,
            "candidate_action": self.candidate_action,
            "backup_required": self.backup_required,
            "backup_method": self.backup_method,
            "deletion_allowed_now": self.deletion_allowed_now,
            "archive_allowed_now": self.archive_allowed_now,
            "rewrite_allowed_now": self.rewrite_allowed_now,
            "required_human_approval": self.required_human_approval,
            "required_backup_evidence": self.required_backup_evidence,
            "required_diff_review": self.required_diff_review,
            "required_owner_note": self.required_owner_note,
            "rollback_plan": self.rollback_plan,
            "final_manual_decision_placeholder": self.final_manual_decision_placeholder,
            "no_touch_until_approved": self.no_touch_until_approved,
        }


def _map_candidate_action(disposition: str, priority: str) -> str:
    """Map queue disposition to a safe candidate action."""
    if disposition in ("CANDIDATE_FOR_ARCHIVE",):
        return "PREPARE_ARCHIVE_AFTER_BACKUP"
    if disposition in ("CANDIDATE_FOR_REWRITE",):
        return "PREPARE_OFFLINE_REWRITE"
    if disposition in ("CANDIDATE_FOR_DELETE",):
        return "PREPARE_DELETE_AFTER_BACKUP"
    if disposition == "NEEDS_HUMAN_REVIEW":
        return "NEEDS_MORE_REVIEW"
    return "KEEP_FROZEN"


def _build_backup_evidence(priority: str, candidate_action: str) -> list[str]:
    evidence = ["sha256_hash_of_file"]
    if priority in ("P0_CRITICAL_REVIEW", "P1_HIGH_REVIEW"):
        evidence.append("full_file_content_backup")
        evidence.append("owner_signoff_on_backup")
    if candidate_action in ("PREPARE_ARCHIVE_AFTER_BACKUP", "PREPARE_DELETE_AFTER_BACKUP"):
        evidence.append("backup_location_recorded")
        evidence.append("backup_integrity_verified")
    return evidence


def _build_rollback_plan(candidate_action: str, path: str) -> str:
    if candidate_action == "PREPARE_ARCHIVE_AFTER_BACKUP":
        return f"Restore {path} from verified backup archive location."
    if candidate_action == "PREPARE_DELETE_AFTER_BACKUP":
        return f"Restore {path} from verified backup before deletion was executed."
    if candidate_action == "PREPARE_OFFLINE_REWRITE":
        return f"Revert to frozen version of {path} from backup if rewrite introduces issues."
    return f"No action planned. {path} remains frozen."


def build_prep_item(queue_item: dict) -> DecisionPrepItem:
    """Build a single DecisionPrepItem from a queue item."""
    disposition = queue_item.get("disposition", "NEEDS_HUMAN_REVIEW")
    priority = queue_item.get("priority", "UNKNOWN_REVIEW")
    candidate_action = _map_candidate_action(disposition, priority)
    path = queue_item["path"]

    needs_backup = candidate_action in (
        "PREPARE_ARCHIVE_AFTER_BACKUP",
        "PREPARE_DELETE_AFTER_BACKUP",
        "PREPARE_OFFLINE_REWRITE",
    )

    return DecisionPrepItem(
        path=path,
        priority=priority,
        current_disposition=disposition,
        candidate_action=candidate_action,
        backup_required=needs_backup,
        backup_method="manual_copy_to_secure_location" if needs_backup else "not_applicable",
        deletion_allowed_now=False,
        archive_allowed_now=False,
        rewrite_allowed_now=False,
        required_human_approval=True,
        required_backup_evidence=_build_backup_evidence(priority, candidate_action),
        required_diff_review=candidate_action in (
            "PREPARE_ARCHIVE_AFTER_BACKUP",
            "PREPARE_DELETE_AFTER_BACKUP",
            "PREPARE_OFFLINE_REWRITE",
        ),
        required_owner_note=priority in ("P0_CRITICAL_REVIEW", "P1_HIGH_REVIEW"),
        rollback_plan=_build_rollback_plan(candidate_action, path),
        final_manual_decision_placeholder="AWAITING_HUMAN_DECISION",
        no_touch_until_approved=True,
    )


def build_decision_prep(
    queue_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[DecisionPrepItem]:
    """Build full decision prep from queue items."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    return [build_prep_item(qi) for qi in queue_items]


def render_decision_prep_markdown(items: list[DecisionPrepItem]) -> str:
    """Render decision prep as markdown."""
    lines = [
        "# Frozen File Archive/Delete Decision Prep",
        "",
        f"**Total items:** {len(items)}",
        f"**release_hold:** HOLD",
        "",
        "## Safety Boundary",
        "",
        "- deletion_allowed_now: **false** for all items",
        "- archive_allowed_now: **false** for all items",
        "- rewrite_allowed_now: **false** for all items",
        "- required_human_approval: **true** for all items",
        "- no_touch_until_approved: **true** for all items",
        "",
        "## Decision Prep Items",
        "",
    ]

    for item in items:
        lines.append(f"### {item.path}")
        lines.append("")
        lines.append(f"- **Priority:** {item.priority}")
        lines.append(f"- **Current Disposition:** {item.current_disposition}")
        lines.append(f"- **Candidate Action:** {item.candidate_action}")
        lines.append(f"- **Backup Required:** {item.backup_required}")
        lines.append(f"- **Backup Method:** {item.backup_method}")
        lines.append(f"- **Deletion Allowed Now:** {item.deletion_allowed_now}")
        lines.append(f"- **Archive Allowed Now:** {item.archive_allowed_now}")
        lines.append(f"- **Rewrite Allowed Now:** {item.rewrite_allowed_now}")
        lines.append(f"- **Required Human Approval:** {item.required_human_approval}")
        lines.append(f"- **Required Diff Review:** {item.required_diff_review}")
        lines.append(f"- **Required Owner Note:** {item.required_owner_note}")
        lines.append(f"- **Rollback Plan:** {item.rollback_plan}")
        lines.append(f"- **Final Decision:** {item.final_manual_decision_placeholder}")
        lines.append(f"- **No Touch Until Approved:** {item.no_touch_until_approved}")
        lines.append("")
        lines.append("**Required Backup Evidence:**")
        for e in item.required_backup_evidence:
            lines.append(f"  - {e}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def load_queue(path: pathlib.Path) -> list[dict]:
    """Load queue items from JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(items: list[DecisionPrepItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(items: list[DecisionPrepItem], out_path: pathlib.Path, release_hold: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "total_items": len(items),
        "candidate_action_counts": {},
        "release_hold": release_hold,
        "deletion_allowed_now": False,
        "archive_allowed_now": False,
        "rewrite_allowed_now": False,
        "required_human_approval": True,
        "no_touch_until_approved": True,
    }
    for item in items:
        manifest["candidate_action_counts"][item.candidate_action] = (
            manifest["candidate_action_counts"].get(item.candidate_action, 0) + 1
        )
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[DecisionPrepItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_decision_prep_markdown(items), encoding="utf-8")
