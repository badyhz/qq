"""T15501 — Frozen Archive Simulation builder.

Pure deterministic. No I/O. No network. No actual file operations.
Reads backup manifest, produces archive simulation items.
Simulation only. No actual archive/delete/move.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_FINAL_STATUSES: tuple[str, ...] = (
    "SIMULATED_READY_FOR_HUMAN_REVIEW",
    "BLOCKED_PENDING_BACKUP",
    "BLOCKED_PENDING_HUMAN_APPROVAL",
    "BLOCKED_UNKNOWN_RISK",
    "KEEP_FROZEN_NO_ACTION",
    "REVIEW_REQUIRED",
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
class ArchiveSimulationItem:
    """Single archive simulation entry."""
    path: str
    proposed_action: str
    simulated_archive_path: str
    simulated_backup_path: str
    required_preconditions: list[str]
    would_copy: bool
    would_move: bool
    would_delete: bool
    would_modify: bool
    simulation_only: bool
    human_approval_required: bool
    backup_required: bool
    rollback_plan_id: str
    blocked_reason_if_any: str
    final_status: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "proposed_action": self.proposed_action,
            "simulated_archive_path": self.simulated_archive_path,
            "simulated_backup_path": self.simulated_backup_path,
            "required_preconditions": self.required_preconditions,
            "would_copy": self.would_copy,
            "would_move": self.would_move,
            "would_delete": self.would_delete,
            "would_modify": self.would_modify,
            "simulation_only": self.simulation_only,
            "human_approval_required": self.human_approval_required,
            "backup_required": self.backup_required,
            "rollback_plan_id": self.rollback_plan_id,
            "blocked_reason_if_any": self.blocked_reason_if_any,
            "final_status": self.final_status,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def _determine_status(backup_item: dict) -> tuple[str, str]:
    """Determine final status and blocking reason from backup manifest item."""
    candidate_action = backup_item.get("candidate_action", "KEEP_FROZEN")
    backup_class = backup_item.get("backup_class", "UNKNOWN")

    if candidate_action == "KEEP_FROZEN":
        return "KEEP_FROZEN_NO_ACTION", ""

    if backup_class == "UNKNOWN":
        return "BLOCKED_UNKNOWN_RISK", "backup_class_unknown_requires_human_review"

    if candidate_action == "NEEDS_MORE_REVIEW":
        return "REVIEW_REQUIRED", "needs_more_human_review"

    if backup_item.get("backup_required", False):
        return "BLOCKED_PENDING_BACKUP", "backup_not_yet_performed_simulation_only"

    return "BLOCKED_PENDING_HUMAN_APPROVAL", "awaiting_human_approval_simulation_only"


def _build_preconditions(backup_item: dict) -> list[str]:
    """Build preconditions list from backup manifest item."""
    preconds = ["human_approval_obtained"]
    if backup_item.get("backup_required", False):
        preconds.append("backup_completed_and_verified")
        preconds.append("backup_hash_verified")
    preconds.append("release_hold_lifted")
    preconds.append("no_frozen_file_touched")
    return preconds


def build_simulation_item(backup_item: dict) -> ArchiveSimulationItem:
    """Build a single archive simulation item from backup manifest item."""
    path = backup_item["path"]
    safe_id = _safe_id(path)
    candidate_action = backup_item.get("candidate_action", "KEEP_FROZEN")
    backup_required = backup_item.get("backup_required", False)

    final_status, blocked_reason = _determine_status(backup_item)

    return ArchiveSimulationItem(
        path=path,
        proposed_action=candidate_action,
        simulated_archive_path=f"archive_simulation/archived/{safe_id}",
        simulated_backup_path=backup_item.get(
            "proposed_backup_path", f"archive_simulation/frozen_files/{safe_id}"
        ),
        required_preconditions=_build_preconditions(backup_item),
        would_copy=False,
        would_move=False,
        would_delete=False,
        would_modify=False,
        simulation_only=True,
        human_approval_required=True,
        backup_required=backup_required,
        rollback_plan_id=backup_item.get("rollback_reference", f"rollback_sim_{safe_id}"),
        blocked_reason_if_any=blocked_reason,
        final_status=final_status,
    )


def build_archive_simulation(
    backup_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[ArchiveSimulationItem]:
    """Build full archive simulation from backup manifest items."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    return [build_simulation_item(bi) for bi in backup_items]


def compute_simulation_hash(items: list[ArchiveSimulationItem]) -> str:
    """Compute deterministic hash of simulation items."""
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_simulation_markdown(items: list[ArchiveSimulationItem]) -> str:
    """Render archive simulation as markdown."""
    lines = [
        "# Frozen File Archive Simulation",
        "",
        f"**Total items:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**simulation_only:** true",
        "",
        "## Safety Boundary",
        "",
        "- would_copy: **false** for all items",
        "- would_move: **false** for all items",
        "- would_delete: **false** for all items",
        "- would_modify: **false** for all items",
        "- simulation_only: **true** for all items",
        "- human_approval_required: **true** for all items",
        "",
        "## Status Summary",
        "",
    ]

    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item.final_status] = status_counts.get(item.final_status, 0) + 1
    for status, count in sorted(status_counts.items()):
        lines.append(f"- **{status}:** {count}")
    lines.append("")

    lines.append("## Simulation Items")
    lines.append("")

    for item in items:
        lines.append(f"### {item.path}")
        lines.append("")
        lines.append(f"- **Proposed Action:** {item.proposed_action}")
        lines.append(f"- **Simulated Archive Path:** {item.simulated_archive_path}")
        lines.append(f"- **Simulated Backup Path:** {item.simulated_backup_path}")
        lines.append(f"- **Final Status:** {item.final_status}")
        lines.append(f"- **Blocked Reason:** {item.blocked_reason_if_any or 'none'}")
        lines.append(f"- **Backup Required:** {item.backup_required}")
        lines.append(f"- **Rollback Plan ID:** {item.rollback_plan_id}")
        lines.append("")
        lines.append("**Required Preconditions:**")
        for p in item.required_preconditions:
            lines.append(f"  - {p}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def load_backup_manifest(path: pathlib.Path) -> list[dict]:
    """Load backup manifest items from JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(items: list[ArchiveSimulationItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(
    items: list[ArchiveSimulationItem],
    out_path: pathlib.Path,
    release_hold: str,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item.final_status] = status_counts.get(item.final_status, 0) + 1
    manifest = {
        "total_items": len(items),
        "status_counts": status_counts,
        "release_hold": release_hold,
        "simulation_only": True,
        "would_copy": False,
        "would_move": False,
        "would_delete": False,
        "would_modify": False,
        "human_approval_required": True,
        "simulation_hash": compute_simulation_hash(items),
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[ArchiveSimulationItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_simulation_markdown(items), encoding="utf-8")
