"""T15501 — Frozen Rollback Plan builder.

Pure deterministic. No I/O. No network. No actual restore operations.
Reads archive simulation, produces rollback plan items.
Documentation only. No executable restore commands.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"


@dataclass(frozen=True)
class RollbackPlanItem:
    """Single rollback plan entry."""
    rollback_plan_id: str
    original_path: str
    simulated_archive_path: str
    simulated_backup_path: str
    rollback_preconditions: list[str]
    required_backup_manifest: str
    required_hash_check: str
    manual_restore_command_template: str
    verification_steps: list[str]
    forbidden_automated_restore: bool
    human_approval_required: bool
    no_execution: bool
    no_import: bool
    release_hold: str

    def to_dict(self) -> dict:
        return {
            "rollback_plan_id": self.rollback_plan_id,
            "original_path": self.original_path,
            "simulated_archive_path": self.simulated_archive_path,
            "simulated_backup_path": self.simulated_backup_path,
            "rollback_preconditions": self.rollback_preconditions,
            "required_backup_manifest": self.required_backup_manifest,
            "required_hash_check": self.required_hash_check,
            "manual_restore_command_template": self.manual_restore_command_template,
            "verification_steps": self.verification_steps,
            "forbidden_automated_restore": self.forbidden_automated_restore,
            "human_approval_required": self.human_approval_required,
            "no_execution": self.no_execution,
            "no_import": self.no_import,
            "release_hold": self.release_hold,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def build_rollback_item(sim_item: dict) -> RollbackPlanItem:
    """Build a single rollback plan item from archive simulation item."""
    path = sim_item["path"]
    safe_id = _safe_id(path)
    rollback_id = sim_item.get("rollback_plan_id", f"rollback_sim_{safe_id}")

    return RollbackPlanItem(
        rollback_plan_id=rollback_id,
        original_path=path,
        simulated_archive_path=sim_item.get(
            "simulated_archive_path", f"archive_simulation/archived/{safe_id}"
        ),
        simulated_backup_path=sim_item.get(
            "simulated_backup_path", f"archive_simulation/frozen_files/{safe_id}"
        ),
        rollback_preconditions=[
            "backup_manifest_hash_verified",
            "human_approval_obtained",
            "release_hold_lifted",
            "backup_integrity_confirmed",
        ],
        required_backup_manifest=f"frozen_backup_manifest/backup_manifest.json#{safe_id}",
        required_hash_check=f"sha256:{safe_id}:verify_before_restore",
        manual_restore_command_template=(
            f"# MANUAL RESTORE TEMPLATE (documentation only, NOT executable by this script)\n"
            f"# Path: {path}\n"
            f"# 1. Verify backup hash matches manifest\n"
            f"# 2. Copy from simulated_backup_path to original_path\n"
            f"# 3. Verify restored file hash matches original\n"
            f"# 4. Confirm with human operator\n"
            f"# cp <backup_path> <original_path>\n"
            f"# sha256sum <original_path>\n"
        ),
        verification_steps=[
            "verify_backup_manifest_hash",
            "verify_backup_file_hash",
            "verify_restored_file_hash",
            "human_confirmation_required",
        ],
        forbidden_automated_restore=True,
        human_approval_required=True,
        no_execution=True,
        no_import=True,
        release_hold=RELEASE_HOLD_REQUIRED,
    )


def build_rollback_plan(
    sim_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[RollbackPlanItem]:
    """Build full rollback plan from archive simulation items."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    return [build_rollback_item(si) for si in sim_items]


def compute_rollback_hash(items: list[RollbackPlanItem]) -> str:
    """Compute deterministic hash of rollback plan items."""
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_rollback_markdown(items: list[RollbackPlanItem]) -> str:
    """Render rollback plan as markdown."""
    lines = [
        "# Frozen File Rollback Plan",
        "",
        f"**Total items:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**forbidden_automated_restore:** true for all items",
        "",
        "## Safety Boundary",
        "",
        "- forbidden_automated_restore: **true** for all items",
        "- human_approval_required: **true** for all items",
        "- no_execution: **true** for all items",
        "- no_import: **true** for all items",
        "",
        "## Rollback Items",
        "",
    ]

    for item in items:
        lines.append(f"### {item.original_path}")
        lines.append("")
        lines.append(f"- **Rollback Plan ID:** {item.rollback_plan_id}")
        lines.append(f"- **Simulated Archive Path:** {item.simulated_archive_path}")
        lines.append(f"- **Simulated Backup Path:** {item.simulated_backup_path}")
        lines.append(f"- **Required Backup Manifest:** {item.required_backup_manifest}")
        lines.append(f"- **Required Hash Check:** {item.required_hash_check}")
        lines.append(f"- **Forbidden Automated Restore:** {item.forbidden_automated_restore}")
        lines.append("")
        lines.append("**Rollback Preconditions:**")
        for p in item.rollback_preconditions:
            lines.append(f"  - {p}")
        lines.append("")
        lines.append("**Verification Steps:**")
        for v in item.verification_steps:
            lines.append(f"  - {v}")
        lines.append("")
        lines.append("**Manual Restore Command Template (documentation only):**")
        lines.append("```")
        lines.append(item.manual_restore_command_template)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
