"""T15501 — Frozen Backup Manifest builder.

Pure deterministic. No I/O. No network. No file operations on frozen files.
Reads decision prep + inventory metadata, produces backup manifest items.
Simulation only. No actual backup copies.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, field

RELEASE_HOLD_REQUIRED = "HOLD"

BACKUP_CLASSES: tuple[str, ...] = (
    "REQUIRED_BEFORE_ARCHIVE",
    "REQUIRED_BEFORE_DELETE",
    "REQUIRED_BEFORE_REWRITE",
    "OPTIONAL_FOR_KEEP_FROZEN",
    "REVIEW_REQUIRED",
    "UNKNOWN",
)

FORBIDDEN_BACKUP_STATUSES: tuple[str, ...] = (
    "BACKUP_DONE",
    "SAFE_TO_DELETE",
    "SAFE_TO_MOVE",
    "SAFE_TO_EXECUTE",
)

FORBIDDEN_FINAL_STATUSES: tuple[str, ...] = (
    "ARCHIVED",
    "DELETED",
    "MOVED",
    "EXECUTED",
    "IMPORTED",
    "ACTIVATED",
)


@dataclass(frozen=True)
class BackupManifestItem:
    """Single backup manifest entry."""
    path: str
    exists: bool
    file_type: str
    size_bytes: int
    sha256: str
    line_count_if_known: int | None
    current_status: str
    current_disposition: str
    priority: str
    candidate_action: str
    backup_required: bool
    backup_allowed_now: bool
    backup_simulation_only: bool
    proposed_backup_id: str
    proposed_backup_path: str
    proposed_backup_manifest_path: str
    required_backup_evidence: list[str]
    required_human_approval: bool
    rollback_reference: str
    no_touch_required: bool
    no_execution: bool
    no_import: bool
    no_stage: bool
    release_hold: str
    advisory_only: bool
    human_review_required: bool
    backup_class: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "exists": self.exists,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "line_count_if_known": self.line_count_if_known,
            "current_status": self.current_status,
            "current_disposition": self.current_disposition,
            "priority": self.priority,
            "candidate_action": self.candidate_action,
            "backup_required": self.backup_required,
            "backup_allowed_now": self.backup_allowed_now,
            "backup_simulation_only": self.backup_simulation_only,
            "proposed_backup_id": self.proposed_backup_id,
            "proposed_backup_path": self.proposed_backup_path,
            "proposed_backup_manifest_path": self.proposed_backup_manifest_path,
            "required_backup_evidence": self.required_backup_evidence,
            "required_human_approval": self.required_human_approval,
            "rollback_reference": self.rollback_reference,
            "no_touch_required": self.no_touch_required,
            "no_execution": self.no_execution,
            "no_import": self.no_import,
            "no_stage": self.no_stage,
            "release_hold": self.release_hold,
            "advisory_only": self.advisory_only,
            "human_review_required": self.human_review_required,
            "backup_class": self.backup_class,
        }


def _safe_id(path: str) -> str:
    """Generate a safe filesystem ID from a path."""
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def _file_type(path: str) -> str:
    """Determine file type from extension."""
    if path.endswith(".py"):
        return "python"
    if path.endswith(".json"):
        return "json"
    if path.endswith(".md"):
        return "markdown"
    if path.endswith(".yaml") or path.endswith(".yml"):
        return "yaml"
    if path.endswith(".sh"):
        return "shell"
    if path.endswith(".html"):
        return "html"
    return "unknown"


def _classify_backup(candidate_action: str, priority: str) -> str:
    """Determine backup class from candidate action."""
    if candidate_action == "PREPARE_ARCHIVE_AFTER_BACKUP":
        return "REQUIRED_BEFORE_ARCHIVE"
    if candidate_action == "PREPARE_DELETE_AFTER_BACKUP":
        return "REQUIRED_BEFORE_DELETE"
    if candidate_action == "PREPARE_OFFLINE_REWRITE":
        return "REQUIRED_BEFORE_REWRITE"
    if candidate_action == "KEEP_FROZEN":
        return "OPTIONAL_FOR_KEEP_FROZEN"
    if candidate_action == "NEEDS_MORE_REVIEW":
        return "REVIEW_REQUIRED"
    return "UNKNOWN"


def _needs_backup(candidate_action: str) -> bool:
    """Check if candidate action requires backup."""
    return candidate_action in (
        "PREPARE_ARCHIVE_AFTER_BACKUP",
        "PREPARE_DELETE_AFTER_BACKUP",
        "PREPARE_OFFLINE_REWRITE",
    )


def build_manifest_item(
    prep_item: dict,
    inventory_meta: dict | None,
    release_hold: str,
) -> BackupManifestItem:
    """Build a single backup manifest item."""
    path = prep_item["path"]
    safe_id = _safe_id(path)
    candidate_action = prep_item.get("candidate_action", "KEEP_FROZEN")
    priority = prep_item.get("priority", "UNKNOWN_REVIEW")

    exists = False
    size_bytes = 0
    sha256 = ""
    line_count = None

    if inventory_meta:
        exists = inventory_meta.get("exists", False)
        size_bytes = inventory_meta.get("size_bytes", 0)
        sha256 = inventory_meta.get("sha256", "")
        line_count = inventory_meta.get("line_count")

    backup_required = _needs_backup(candidate_action)
    backup_class = _classify_backup(candidate_action, priority)

    return BackupManifestItem(
        path=path,
        exists=exists,
        file_type=_file_type(path),
        size_bytes=size_bytes,
        sha256=sha256,
        line_count_if_known=line_count,
        current_status="FROZEN_NO_TOUCH",
        current_disposition=prep_item.get("current_disposition", "UNKNOWN"),
        priority=priority,
        candidate_action=candidate_action,
        backup_required=backup_required,
        backup_allowed_now=False,
        backup_simulation_only=True,
        proposed_backup_id=f"backup_sim_{safe_id}",
        proposed_backup_path=f"archive_simulation/frozen_files/{safe_id}",
        proposed_backup_manifest_path=f"archive_simulation/frozen_files/{safe_id}.manifest.json",
        required_backup_evidence=prep_item.get("required_backup_evidence", ["sha256_hash_of_file"]),
        required_human_approval=True,
        rollback_reference=f"rollback_sim_{safe_id}",
        no_touch_required=True,
        no_execution=True,
        no_import=True,
        no_stage=True,
        release_hold=release_hold,
        advisory_only=True,
        human_review_required=True,
        backup_class=backup_class,
    )


def build_backup_manifest(
    prep_items: list[dict],
    inventory_files: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[BackupManifestItem]:
    """Build full backup manifest from decision prep + inventory."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    inv_map: dict[str, dict] = {f["path"]: f for f in inventory_files}

    return [
        build_manifest_item(pi, inv_map.get(pi["path"]), release_hold)
        for pi in prep_items
    ]


def compute_manifest_hash(items: list[BackupManifestItem]) -> str:
    """Compute deterministic hash of manifest items."""
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_manifest_markdown(items: list[BackupManifestItem]) -> str:
    """Render backup manifest as markdown."""
    lines = [
        "# Frozen File Backup Manifest",
        "",
        f"**Total items:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**simulation_only:** true",
        "",
        "## Safety Boundary",
        "",
        "- backup_allowed_now: **false** for all items",
        "- required_human_approval: **true** for all items",
        "- no_touch_required: **true** for all items",
        "- backup_simulation_only: **true** for all items",
        "- advisory_only: **true** for all items",
        "",
        "## Backup Classes",
        "",
    ]

    class_counts: dict[str, int] = {}
    for item in items:
        class_counts[item.backup_class] = class_counts.get(item.backup_class, 0) + 1
    for cls, count in sorted(class_counts.items()):
        lines.append(f"- **{cls}:** {count}")
    lines.append("")

    lines.append("## Manifest Items")
    lines.append("")

    for item in items:
        lines.append(f"### {item.path}")
        lines.append("")
        lines.append(f"- **Exists:** {item.exists}")
        lines.append(f"- **File Type:** {item.file_type}")
        lines.append(f"- **Size:** {item.size_bytes} bytes")
        lines.append(f"- **SHA256:** `{item.sha256}`")
        lines.append(f"- **Current Status:** {item.current_status}")
        lines.append(f"- **Candidate Action:** {item.candidate_action}")
        lines.append(f"- **Backup Class:** {item.backup_class}")
        lines.append(f"- **Backup Required:** {item.backup_required}")
        lines.append(f"- **Backup Allowed Now:** {item.backup_allowed_now}")
        lines.append(f"- **Proposed Backup ID:** {item.proposed_backup_id}")
        lines.append(f"- **Proposed Backup Path:** {item.proposed_backup_path}")
        lines.append(f"- **Rollback Reference:** {item.rollback_reference}")
        lines.append(f"- **Release Hold:** {item.release_hold}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def load_decision_prep(path: pathlib.Path) -> list[dict]:
    """Load decision prep items from JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_inventory_files(path: pathlib.Path) -> list[dict]:
    """Load inventory files from JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("files", data) if isinstance(data, dict) else data


def write_json(items: list[BackupManifestItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(
    items: list[BackupManifestItem],
    out_path: pathlib.Path,
    release_hold: str,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    class_counts: dict[str, int] = {}
    for item in items:
        class_counts[item.backup_class] = class_counts.get(item.backup_class, 0) + 1
    manifest = {
        "total_items": len(items),
        "backup_class_counts": class_counts,
        "release_hold": release_hold,
        "backup_allowed_now": False,
        "required_human_approval": True,
        "simulation_only": True,
        "advisory_only": True,
        "manifest_hash": compute_manifest_hash(items),
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[BackupManifestItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_manifest_markdown(items), encoding="utf-8")
