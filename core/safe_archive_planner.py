"""T25002 — Safe Archive Planner.

Pure deterministic. No I/O. No network.
Generates archive plan for ARCHIVE_CANDIDATE files.
Currently no archive candidates exist — module handles empty case properly.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from core.untracked_runtime_inventory import (
    UntrackedFileRecord,
    build_inventory,
    RELEASE_HOLD_REQUIRED,
)

RELEASE_HOLD_REQUIRED_ARC = "HOLD"


@dataclass(frozen=True)
class ArchiveAction:
    """Single archive action for a candidate file."""
    action_id: str
    path: str
    risk_reason: str
    archive_action: str  # "SIMULATE_ARCHIVE" or "SKIP"
    would_copy: bool
    would_move: bool
    would_delete: bool
    human_approval_required: bool
    simulation_only: bool
    advisory_only: bool

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "path": self.path,
            "risk_reason": self.risk_reason,
            "archive_action": self.archive_action,
            "would_copy": self.would_copy,
            "would_move": self.would_move,
            "would_delete": self.would_delete,
            "human_approval_required": self.human_approval_required,
            "simulation_only": self.simulation_only,
            "advisory_only": self.advisory_only,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def build_archive_action(record: UntrackedFileRecord) -> ArchiveAction:
    """Build an archive action for an archive candidate."""
    return ArchiveAction(
        action_id=f"arc_{_safe_id(record.path)}",
        path=record.path,
        risk_reason=record.risk_reason,
        archive_action="SIMULATE_ARCHIVE",
        would_copy=False,
        would_move=False,
        would_delete=False,
        human_approval_required=True,
        simulation_only=True,
        advisory_only=True,
    )


def build_archive_plan(
    release_hold: str = RELEASE_HOLD_REQUIRED_ARC,
) -> list[ArchiveAction]:
    """Build archive plan for all archive candidate files."""
    if release_hold != RELEASE_HOLD_REQUIRED_ARC:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    records = build_inventory(release_hold=RELEASE_HOLD_REQUIRED)
    return [
        build_archive_action(r)
        for r in records
        if r.risk_category == "ARCHIVE_CANDIDATE"
    ]


def compute_archive_hash(actions: list[ArchiveAction]) -> str:
    raw = json.dumps([a.to_dict() for a in actions], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_archive_plan_markdown(actions: list[ArchiveAction]) -> str:
    lines = [
        "# Safe Archive Plan",
        "",
        f"**Archive candidates:** {len(actions)}",
        "",
    ]
    if not actions:
        lines.append("No archive candidates identified in current inventory.")
        lines.append("")
        lines.append("All untracked files are classified as:")
        lines.append("- SAFE_* (integrate into governance stack)")
        lines.append("- SHADOW_PIPELINE / ALERT_PIPELINE (connect to pipeline)")
        lines.append("- TESTNET_DRY_RUN_ONLY (wrap in dry-run adapter)")
        lines.append("- HIGH_RISK_* (isolate, require human approval)")
        lines.append("- NEEDS_HUMAN_REVIEW (queue for human decision)")
        lines.append("")
    else:
        for a in actions:
            lines.append(f"### {a.path}")
            lines.append(f"- **Reason:** {a.risk_reason}")
            lines.append(f"- **Action:** {a.archive_action}")
            lines.append(f"- **Simulation only:** {a.simulation_only}")
            lines.append(f"- **Human approval required:** {a.human_approval_required}")
            lines.append("")
    return "\n".join(lines)


def write_json(actions: list[ArchiveAction], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([a.to_dict() for a in actions], indent=2), encoding="utf-8")


def write_manifest(actions: list[ArchiveAction], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "total_archive_candidates": len(actions),
        "release_hold": release_hold,
        "archive_hash": compute_archive_hash(actions),
        "all_simulation_only": all(a.simulation_only for a in actions) if actions else True,
        "all_advisory_only": all(a.advisory_only for a in actions) if actions else True,
        "all_require_human_approval": all(a.human_approval_required for a in actions) if actions else True,
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
