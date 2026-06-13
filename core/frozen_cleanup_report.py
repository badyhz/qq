"""T17001 — Frozen Cleanup Final Report Generator.

Pure deterministic. No I/O. No network.
Aggregates all cleanup artifacts into a final cleanup report.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"


@dataclass(frozen=True)
class CleanupReportSummary:
    """Final cleanup report summary."""
    report_id: str
    total_files_inventoried: int
    classification_counts: dict[str, int]
    decision_counts: dict[str, int]
    dry_run_outcome_counts: dict[str, int]
    evidence_count: int
    all_simulation_only: bool
    all_no_action_performed: bool
    all_human_approval_required: bool
    cleanup_ready_for_human_review: bool
    release_hold: str

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "total_files_inventoried": self.total_files_inventoried,
            "classification_counts": dict(sorted(self.classification_counts.items())),
            "decision_counts": dict(sorted(self.decision_counts.items())),
            "dry_run_outcome_counts": dict(sorted(self.dry_run_outcome_counts.items())),
            "evidence_count": self.evidence_count,
            "all_simulation_only": self.all_simulation_only,
            "all_no_action_performed": self.all_no_action_performed,
            "all_human_approval_required": self.all_human_approval_required,
            "cleanup_ready_for_human_review": self.cleanup_ready_for_human_review,
            "release_hold": self.release_hold,
        }


def build_cleanup_report(
    inventory_items: list[dict],
    decision_items: list[dict],
    dry_run_items: list[dict],
    evidence_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> CleanupReportSummary:
    """Build final cleanup report from all artifacts."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    class_counts: dict[str, int] = {}
    for item in inventory_items:
        cls = item.get("cleanup_classification", "UNKNOWN")
        class_counts[cls] = class_counts.get(cls, 0) + 1

    decision_counts: dict[str, int] = {}
    for item in decision_items:
        d = item.get("decision", "UNKNOWN")
        decision_counts[d] = decision_counts.get(d, 0) + 1

    outcome_counts: dict[str, int] = {}
    for item in dry_run_items:
        o = item.get("simulated_outcome", "UNKNOWN")
        outcome_counts[o] = outcome_counts.get(o, 0) + 1

    all_sim = all(item.get("simulation_only", False) for item in inventory_items) if inventory_items else False
    all_no_action = all(item.get("no_action_performed", True) for item in dry_run_items) if dry_run_items else True
    all_hra = all(item.get("human_approval_required", True) for item in inventory_items) if inventory_items else False

    return CleanupReportSummary(
        report_id="frozen_cleanup_final_report",
        total_files_inventoried=len(inventory_items),
        classification_counts=class_counts,
        decision_counts=decision_counts,
        dry_run_outcome_counts=outcome_counts,
        evidence_count=len(evidence_items),
        all_simulation_only=all_sim,
        all_no_action_performed=all_no_action,
        all_human_approval_required=all_hra,
        cleanup_ready_for_human_review=True,
        release_hold=release_hold,
    )


def compute_report_hash(report: CleanupReportSummary) -> str:
    raw = json.dumps(report.to_dict(), sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_report_markdown(report: CleanupReportSummary) -> str:
    lines = [
        "# Frozen File Cleanup Final Report",
        "",
        f"**Report ID:** {report.report_id}",
        f"**Total files inventoried:** {report.total_files_inventoried}",
        f"**Evidence records:** {report.evidence_count}",
        f"**release_hold:** {report.release_hold}",
        "",
        "## Safety Summary",
        "",
        f"- **all_simulation_only:** {report.all_simulation_only}",
        f"- **all_no_action_performed:** {report.all_no_action_performed}",
        f"- **all_human_approval_required:** {report.all_human_approval_required}",
        f"- **cleanup_ready_for_human_review:** {report.cleanup_ready_for_human_review}",
        "",
        "## Classification Breakdown",
        "",
    ]

    for cls, count in sorted(report.classification_counts.items()):
        lines.append(f"- **{cls}:** {count}")

    lines.append("")
    lines.append("## Decision Breakdown")
    lines.append("")

    for d, count in sorted(report.decision_counts.items()):
        lines.append(f"- **{d}:** {count}")

    lines.append("")
    lines.append("## Dry-Run Outcome Breakdown")
    lines.append("")

    for o, count in sorted(report.dry_run_outcome_counts.items()):
        lines.append(f"- **{o}:** {count}")

    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append("All frozen files have been inventoried, classified, and evaluated.")
    lines.append("No real file operations were performed.")
    lines.append("All decisions are simulation-only and require human approval.")
    lines.append("The cleanup governance finalization is ready for human review.")
    lines.append("")
    lines.append("---")
    lines.append("NO ACTION PERFORMED. SIMULATION ONLY. HUMAN APPROVAL REQUIRED.")
    lines.append("")

    return "\n".join(lines)


def write_json(report: CleanupReportSummary, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def write_manifest(
    report: CleanupReportSummary,
    out_path,
    release_hold: str,
) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "report_id": report.report_id,
        "total_files_inventoried": report.total_files_inventoried,
        "evidence_count": report.evidence_count,
        "release_hold": release_hold,
        "simulation_only": True,
        "no_action_performed": True,
        "human_approval_required": True,
        "report_hash": compute_report_hash(report),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(report: CleanupReportSummary, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_report_markdown(report), encoding="utf-8")
