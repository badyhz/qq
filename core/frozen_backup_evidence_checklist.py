"""T16001 — Frozen Backup Evidence Checklist builder.

Pure deterministic. No I/O. No network. No file operations on frozen files.
Reads backup manifest + archive simulation metadata, produces evidence checklist items.
No actual backup/archive/delete/move/copy operations performed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, field

RELEASE_HOLD_REQUIRED = "HOLD"

FORBIDDEN_CHECKLIST_STATUSES: tuple[str, ...] = (
    "COMPLETE",
    "BACKUP_DONE",
    "APPROVED",
    "SAFE_TO_DELETE",
    "SAFE_TO_MOVE",
    "SAFE_TO_EXECUTE",
    "ARCHIVED",
    "DELETED",
    "MOVED",
    "EXECUTED",
    "IMPORTED",
    "ACTIVATED",
)

BLOCKER_STATUSES: tuple[str, ...] = (
    "BLOCKED_PENDING_EVIDENCE",
    "BLOCKED_PENDING_OWNER",
    "BLOCKED_PENDING_HASH_REVIEW",
    "BLOCKED_PENDING_ROLLBACK_REVIEW",
    "BLOCKED_PENDING_HUMAN_APPROVAL",
    "REVIEW_REQUIRED",
)

REQUIRED_EVIDENCE_FIELDS: tuple[str, ...] = (
    "original_path_confirmed",
    "original_sha256_recorded",
    "original_size_recorded",
    "original_status_recorded",
    "proposed_backup_path_reviewed",
    "rollback_plan_reviewed",
    "human_owner_assigned",
    "human_approval_pending",
    "no_touch_confirmed",
    "forbidden_actions_acknowledged",
)


@dataclass(frozen=True)
class EvidenceChecklistItem:
    """Single backup evidence checklist entry."""
    checklist_id: str
    path: str
    priority: str
    candidate_action: str
    backup_class: str
    required_evidence: list[str]
    required_hash_evidence: list[str]
    required_size_evidence: list[str]
    required_path_evidence: list[str]
    required_owner_note: str
    required_review_note: str
    required_rollback_note: str
    evidence_status: str
    blocker_status: str
    evidence_paths_placeholder: list[str]
    no_touch_required: bool
    backup_not_performed: bool
    archive_not_performed: bool
    delete_not_performed: bool
    copy_not_performed: bool
    move_not_performed: bool
    release_hold: str
    advisory_only: bool
    human_review_required: bool

    def to_dict(self) -> dict:
        return {
            "checklist_id": self.checklist_id,
            "path": self.path,
            "priority": self.priority,
            "candidate_action": self.candidate_action,
            "backup_class": self.backup_class,
            "required_evidence": self.required_evidence,
            "required_hash_evidence": self.required_hash_evidence,
            "required_size_evidence": self.required_size_evidence,
            "required_path_evidence": self.required_path_evidence,
            "required_owner_note": self.required_owner_note,
            "required_review_note": self.required_review_note,
            "required_rollback_note": self.required_rollback_note,
            "evidence_status": self.evidence_status,
            "blocker_status": self.blocker_status,
            "evidence_paths_placeholder": self.evidence_paths_placeholder,
            "no_touch_required": self.no_touch_required,
            "backup_not_performed": self.backup_not_performed,
            "archive_not_performed": self.archive_not_performed,
            "delete_not_performed": self.delete_not_performed,
            "copy_not_performed": self.copy_not_performed,
            "move_not_performed": self.move_not_performed,
            "release_hold": self.release_hold,
            "advisory_only": self.advisory_only,
            "human_review_required": self.human_review_required,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def _determine_blocker(candidate_action: str) -> str:
    if candidate_action in ("PREPARE_ARCHIVE_AFTER_BACKUP", "PREPARE_DELETE_AFTER_BACKUP"):
        return "BLOCKED_PENDING_EVIDENCE"
    if candidate_action == "PREPARE_OFFLINE_REWRITE":
        return "BLOCKED_PENDING_EVIDENCE"
    if candidate_action == "KEEP_FROZEN":
        return "BLOCKED_PENDING_HUMAN_APPROVAL"
    if candidate_action == "NEEDS_MORE_REVIEW":
        return "REVIEW_REQUIRED"
    return "BLOCKED_PENDING_EVIDENCE"


def _hash_evidence(sha256: str) -> list[str]:
    items = ["original_sha256_recorded", "hash_independently_verified"]
    if sha256:
        items.append(f"known_hash={sha256}")
    return items


def _size_evidence(size_bytes: int) -> list[str]:
    return ["original_size_recorded", f"known_size={size_bytes}_bytes"]


def _path_evidence(path: str, proposed_backup_path: str) -> list[str]:
    return [
        "original_path_confirmed",
        f"original_path={path}",
        "proposed_backup_path_reviewed",
        f"proposed_backup_path={proposed_backup_path}",
    ]


def build_checklist_item(
    manifest_item: dict,
    sim_item: dict | None,
    release_hold: str,
) -> EvidenceChecklistItem:
    """Build a single evidence checklist item."""
    path = manifest_item["path"]
    safe_id = _safe_id(path)
    candidate_action = manifest_item.get("candidate_action", "KEEP_FROZEN")
    priority = manifest_item.get("priority", "UNKNOWN_REVIEW")
    backup_class = manifest_item.get("backup_class", "UNKNOWN")
    sha256 = manifest_item.get("sha256", "")
    size_bytes = manifest_item.get("size_bytes", 0)
    proposed_backup_path = manifest_item.get("proposed_backup_path", "")
    rollback_ref = manifest_item.get("rollback_reference", "")

    return EvidenceChecklistItem(
        checklist_id=f"checklist_{safe_id}",
        path=path,
        priority=priority,
        candidate_action=candidate_action,
        backup_class=backup_class,
        required_evidence=list(REQUIRED_EVIDENCE_FIELDS),
        required_hash_evidence=_hash_evidence(sha256),
        required_size_evidence=_size_evidence(size_bytes),
        required_path_evidence=_path_evidence(path, proposed_backup_path),
        required_owner_note="HUMAN_MUST_ASSIGN_OWNER",
        required_review_note="HUMAN_MUST_REVIEW_EVIDENCE",
        required_rollback_note=f"rollback_plan={rollback_ref}_HUMAN_MUST_REVIEW",
        evidence_status="PENDING",
        blocker_status=_determine_blocker(candidate_action),
        evidence_paths_placeholder=[
            f"evidence/{safe_id}/hash_record.json",
            f"evidence/{safe_id}/size_record.json",
            f"evidence/{safe_id}/path_confirmation.json",
            f"evidence/{safe_id}/owner_assignment.json",
            f"evidence/{safe_id}/rollback_plan.json",
        ],
        no_touch_required=True,
        backup_not_performed=True,
        archive_not_performed=True,
        delete_not_performed=True,
        copy_not_performed=True,
        move_not_performed=True,
        release_hold=release_hold,
        advisory_only=True,
        human_review_required=True,
    )


def build_evidence_checklist(
    manifest_items: list[dict],
    sim_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[EvidenceChecklistItem]:
    """Build full evidence checklist from backup manifest + archive simulation."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    sim_map: dict[str, dict] = {}
    for s in sim_items:
        sim_map[s.get("path", "")] = s

    return [
        build_checklist_item(mi, sim_map.get(mi["path"]), release_hold)
        for mi in manifest_items
    ]


def compute_checklist_hash(items: list[EvidenceChecklistItem]) -> str:
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_checklist_markdown(items: list[EvidenceChecklistItem]) -> str:
    lines = [
        "# Frozen File Backup Evidence Checklist",
        "",
        f"**Total items:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**evidence_status:** PENDING for all items",
        "",
        "## Safety Boundary",
        "",
        "- No item is COMPLETE.",
        "- No item is BACKUP_DONE.",
        "- No item is APPROVED.",
        "- No item is SAFE_TO_DELETE.",
        "- All items require human evidence collection before any action.",
        "- All items: backup_not_performed=true, archive_not_performed=true, delete_not_performed=true.",
        "- release_hold=HOLD, advisory_only=true, human_review_required=true.",
        "",
        "## Blocker Status Summary",
        "",
    ]

    blocker_counts: dict[str, int] = {}
    for item in items:
        blocker_counts[item.blocker_status] = blocker_counts.get(item.blocker_status, 0) + 1
    for bs, count in sorted(blocker_counts.items()):
        lines.append(f"- **{bs}:** {count}")
    lines.append("")

    lines.append("## Checklist Items")
    lines.append("")

    for item in items:
        lines.append(f"### {item.path}")
        lines.append("")
        lines.append(f"- **checklist_id:** {item.checklist_id}")
        lines.append(f"- **priority:** {item.priority}")
        lines.append(f"- **candidate_action:** {item.candidate_action}")
        lines.append(f"- **backup_class:** {item.backup_class}")
        lines.append(f"- **evidence_status:** {item.evidence_status}")
        lines.append(f"- **blocker_status:** {item.blocker_status}")
        lines.append(f"- **required_owner_note:** {item.required_owner_note}")
        lines.append(f"- **required_review_note:** {item.required_review_note}")
        lines.append(f"- **required_rollback_note:** {item.required_rollback_note}")
        lines.append(f"- **release_hold:** {item.release_hold}")
        lines.append("")
        lines.append("**Required Evidence:**")
        for ev in item.required_evidence:
            lines.append(f"  - {ev}")
        lines.append("")
        lines.append("**Required Hash Evidence:**")
        for ev in item.required_hash_evidence:
            lines.append(f"  - {ev}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def load_manifest_items(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("items", [])


def load_sim_items(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("items", [])


def write_json(items: list[EvidenceChecklistItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(
    items: list[EvidenceChecklistItem],
    out_path: pathlib.Path,
    release_hold: str,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    blocker_counts: dict[str, int] = {}
    for item in items:
        blocker_counts[item.blocker_status] = blocker_counts.get(item.blocker_status, 0) + 1
    manifest = {
        "total_items": len(items),
        "blocker_counts": blocker_counts,
        "release_hold": release_hold,
        "evidence_status_all_pending": all(i.evidence_status == "PENDING" for i in items),
        "no_item_complete": all(i.evidence_status != "COMPLETE" for i in items),
        "no_backup_done": True,
        "no_approved": True,
        "no_safe_to_delete": True,
        "advisory_only": True,
        "human_review_required": True,
        "checklist_hash": compute_checklist_hash(items),
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[EvidenceChecklistItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_checklist_markdown(items), encoding="utf-8")
