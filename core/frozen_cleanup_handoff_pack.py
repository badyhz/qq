"""T17001 — Frozen Cleanup Handoff Pack Generator.

Pure deterministic. No I/O. No network.
Generates the final cleanup handoff pack for human review.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"


@dataclass(frozen=True)
class HandoffPackItem:
    """Single item in the cleanup handoff pack."""
    item_id: str
    artifact_type: str
    artifact_name: str
    artifact_path: str
    description: str
    status: str
    simulation_only: bool
    human_review_required: bool

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "artifact_type": self.artifact_type,
            "artifact_name": self.artifact_name,
            "artifact_path": self.artifact_path,
            "description": self.description,
            "status": self.status,
            "simulation_only": self.simulation_only,
            "human_review_required": self.human_review_required,
        }


@dataclass(frozen=True)
class CleanupHandoffPack:
    """Complete cleanup handoff pack."""
    pack_id: str
    items: list[HandoffPackItem]
    total_artifacts: int
    all_simulation_only: bool
    all_human_review_required: bool
    release_hold: str
    next_steps: list[str]

    def to_dict(self) -> dict:
        return {
            "pack_id": self.pack_id,
            "items": [i.to_dict() for i in self.items],
            "total_artifacts": self.total_artifacts,
            "all_simulation_only": self.all_simulation_only,
            "all_human_review_required": self.all_human_review_required,
            "release_hold": self.release_hold,
            "next_steps": self.next_steps,
        }


def build_handoff_pack(
    inventory_path: str,
    decision_matrix_path: str,
    dry_run_report_path: str,
    evidence_path: str,
    final_report_path: str,
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> CleanupHandoffPack:
    """Build cleanup handoff pack from artifact paths."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    artifacts = [
        ("inventory", "final_inventory", inventory_path,
         "Complete frozen file final inventory with classifications"),
        ("decision_matrix", "decision_matrix", decision_matrix_path,
         "Cleanup decision matrix with Archive/Retain/Review/Reject decisions"),
        ("dry_run_report", "dry_run_report", dry_run_report_path,
         "Dry-run execution report for all cleanup decisions"),
        ("evidence", "cleanup_evidence", evidence_path,
         "Evidence records for all cleanup governance steps"),
        ("final_report", "final_report", final_report_path,
         "Final cleanup governance report summary"),
    ]

    items: list[HandoffPackItem] = []
    for art_type, art_name, art_path, desc in artifacts:
        items.append(HandoffPackItem(
            item_id=f"handoff_{art_name}",
            artifact_type=art_type,
            artifact_name=art_name,
            artifact_path=art_path,
            description=desc,
            status="GENERATED",
            simulation_only=True,
            human_review_required=True,
        ))

    return CleanupHandoffPack(
        pack_id="frozen_cleanup_handoff_pack",
        items=items,
        total_artifacts=len(items),
        all_simulation_only=True,
        all_human_review_required=True,
        release_hold=release_hold,
        next_steps=[
            "HUMAN_REVIEW: Review all generated artifacts",
            "HUMAN_DECISION: Approve or reject cleanup classifications",
            "HUMAN_APPROVAL: Obtain explicit approval before any file operations",
            "EVIDENCE: Verify all evidence records are complete",
            "BLOCKER: Clear all blockers before proceeding",
        ],
    )


def compute_handoff_hash(pack: CleanupHandoffPack) -> str:
    raw = json.dumps(pack.to_dict(), sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_handoff_markdown(pack: CleanupHandoffPack) -> str:
    lines = [
        "# Frozen Cleanup Handoff Pack",
        "",
        f"**Pack ID:** {pack.pack_id}",
        f"**Total artifacts:** {pack.total_artifacts}",
        f"**release_hold:** {pack.release_hold}",
        "",
        "## Safety Summary",
        "",
        f"- **all_simulation_only:** {pack.all_simulation_only}",
        f"- **all_human_review_required:** {pack.all_human_review_required}",
        "",
        "## Artifacts",
        "",
    ]

    for item in pack.items:
        lines.append(f"### {item.artifact_name}")
        lines.append("")
        lines.append(f"- **type:** {item.artifact_type}")
        lines.append(f"- **path:** {item.artifact_path}")
        lines.append(f"- **description:** {item.description}")
        lines.append(f"- **status:** {item.status}")
        lines.append(f"- **simulation_only:** {item.simulation_only}")
        lines.append(f"- **human_review_required:** {item.human_review_required}")
        lines.append("")

    lines.append("## Next Steps")
    lines.append("")

    for step in pack.next_steps:
        lines.append(f"- {step}")

    lines.append("")
    lines.append("---")
    lines.append("HANDOFF PACK GENERATED. NO ACTION PERFORMED. HUMAN REVIEW REQUIRED.")
    lines.append("")

    return "\n".join(lines)


def write_json(pack: CleanupHandoffPack, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(pack.to_dict(), indent=2), encoding="utf-8")


def write_manifest(
    pack: CleanupHandoffPack,
    out_path,
    release_hold: str,
) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "pack_id": pack.pack_id,
        "total_artifacts": pack.total_artifacts,
        "release_hold": release_hold,
        "simulation_only": True,
        "human_review_required": True,
        "handoff_hash": compute_handoff_hash(pack),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(pack: CleanupHandoffPack, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_handoff_markdown(pack), encoding="utf-8")
