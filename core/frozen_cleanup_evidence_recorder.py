"""T17001 — Frozen Cleanup Evidence Recorder.

Pure deterministic. No I/O. No network. No actual file operations.
Records evidence for cleanup decisions without performing any real action.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_EVIDENCE_TYPES: tuple[str, ...] = (
    "INVENTORY_COMPLETE",
    "DECISION_MATRIX_GENERATED",
    "DRY_RUN_EXECUTED",
    "BACKUP_MANIFEST_REVIEWED",
    "ARCHIVE_SIMULATION_REVIEWED",
    "APPROVAL_STATUS_RECORDED",
    "BLOCKER_STATUS_RECORDED",
    "HANDOFF_PACK_GENERATED",
)

FORBIDDEN_EVIDENCE_TYPES: tuple[str, ...] = (
    "FILE_DELETED",
    "FILE_MOVED",
    "FILE_MODIFIED",
    "FILE_EXECUTED",
    "APPROVAL_GRANTED",
    "CLEANUP_COMPLETED",
)


@dataclass(frozen=True)
class CleanupEvidenceRecord:
    """Single cleanup evidence record."""
    evidence_id: str
    path: str
    evidence_type: str
    evidence_description: str
    source_module: str
    verified: bool
    human_reviewed: bool
    no_action_performed: bool
    simulation_only: bool
    advisory_only: bool

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "path": self.path,
            "evidence_type": self.evidence_type,
            "evidence_description": self.evidence_description,
            "source_module": self.source_module,
            "verified": self.verified,
            "human_reviewed": self.human_reviewed,
            "no_action_performed": self.no_action_performed,
            "simulation_only": self.simulation_only,
            "advisory_only": self.advisory_only,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def build_evidence_record(
    path: str,
    evidence_type: str,
    description: str,
    source_module: str,
) -> CleanupEvidenceRecord:
    """Build a single evidence record."""
    safe_id = _safe_id(path)
    return CleanupEvidenceRecord(
        evidence_id=f"evidence_{safe_id}_{evidence_type.lower()}",
        path=path,
        evidence_type=evidence_type,
        evidence_description=description,
        source_module=source_module,
        verified=True,
        human_reviewed=False,
        no_action_performed=True,
        simulation_only=True,
        advisory_only=True,
    )


def build_evidence_from_inventory(
    inventory_items: list[dict],
) -> list[CleanupEvidenceRecord]:
    """Build evidence records from inventory items."""
    records: list[CleanupEvidenceRecord] = []
    for item in inventory_items:
        path = item.get("path", "unknown")
        records.append(build_evidence_record(
            path=path,
            evidence_type="INVENTORY_COMPLETE",
            description=f"file_tracked_in_final_inventory_source={item.get('source', 'unknown')}",
            source_module="frozen_cleanup_final_inventory",
        ))
    return records


def build_evidence_from_decisions(
    decision_items: list[dict],
) -> list[CleanupEvidenceRecord]:
    """Build evidence records from decision matrix items."""
    records: list[CleanupEvidenceRecord] = []
    for item in decision_items:
        path = item.get("path", "unknown")
        decision = item.get("decision", "UNKNOWN")
        records.append(build_evidence_record(
            path=path,
            evidence_type="DECISION_MATRIX_GENERATED",
            description=f"cleanup_decision={decision}_reason={item.get('decision_reason', 'unknown')}",
            source_module="frozen_cleanup_decision_matrix",
        ))
    return records


def build_evidence_from_dry_run(
    dry_run_items: list[dict],
) -> list[CleanupEvidenceRecord]:
    """Build evidence records from dry-run results."""
    records: list[CleanupEvidenceRecord] = []
    for item in dry_run_items:
        path = item.get("path", "unknown")
        outcome = item.get("simulated_outcome", "UNKNOWN")
        records.append(build_evidence_record(
            path=path,
            evidence_type="DRY_RUN_EXECUTED",
            description=f"dry_run_outcome={outcome}_no_action_performed",
            source_module="frozen_cleanup_dry_run_executor",
        ))
    return records


def build_all_evidence(
    inventory_items: list[dict],
    decision_items: list[dict],
    dry_run_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[CleanupEvidenceRecord]:
    """Build all cleanup evidence records."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    records: list[CleanupEvidenceRecord] = []
    records.extend(build_evidence_from_inventory(inventory_items))
    records.extend(build_evidence_from_decisions(decision_items))
    records.extend(build_evidence_from_dry_run(dry_run_items))
    return records


def compute_evidence_hash(items: list[CleanupEvidenceRecord]) -> str:
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_evidence_markdown(items: list[CleanupEvidenceRecord]) -> str:
    lines = [
        "# Frozen Cleanup Evidence Records",
        "",
        f"**Total evidence records:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**simulation_only:** true for all records",
        f"**no_action_performed:** true for all records",
        "",
        "## Safety Boundary",
        "",
        "- No evidence record indicates a completed action.",
        "- All records are simulation-only and advisory.",
        "- No file has been deleted, moved, modified, or executed.",
        "",
        "## Evidence Type Summary",
        "",
    ]

    type_counts: dict[str, int] = {}
    for item in items:
        type_counts[item.evidence_type] = type_counts.get(item.evidence_type, 0) + 1
    for et, count in sorted(type_counts.items()):
        lines.append(f"- **{et}:** {count}")

    lines.append("")
    lines.append("## Evidence Records")
    lines.append("")

    for item in items:
        lines.append(f"- **{item.evidence_id}:** {item.evidence_type} — {item.evidence_description}")

    lines.append("")
    lines.append("---")
    lines.append("ALL EVIDENCE IS SIMULATION-ONLY. NO ACTION PERFORMED.")
    lines.append("")

    return "\n".join(lines)


def write_json(items: list[CleanupEvidenceRecord], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(
    items: list[CleanupEvidenceRecord],
    out_path,
    release_hold: str,
) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    type_counts: dict[str, int] = {}
    for item in items:
        type_counts[item.evidence_type] = type_counts.get(item.evidence_type, 0) + 1
    manifest = {
        "total_evidence": len(items),
        "type_counts": dict(sorted(type_counts.items())),
        "release_hold": release_hold,
        "simulation_only": True,
        "no_action_performed": True,
        "advisory_only": True,
        "evidence_hash": compute_evidence_hash(items),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[CleanupEvidenceRecord], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_evidence_markdown(items), encoding="utf-8")
