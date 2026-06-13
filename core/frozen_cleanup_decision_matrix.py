"""T17001 — Frozen File Cleanup Decision Matrix.

Pure deterministic. No I/O. No network. No actual file operations.
Reads final inventory, produces cleanup decision matrix with
Archive / Retain / Review / Reject classifications.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_DECISIONS: tuple[str, ...] = (
    "ARCHIVE_PROPOSED",
    "RETAIN_FROZEN",
    "REVIEW_REQUIRED",
    "REJECT_FROM_CLEANUP",
)

FORBIDDEN_DECISIONS: tuple[str, ...] = (
    "ARCHIVE_NOW",
    "DELETE_NOW",
    "MOVE_NOW",
    "MODIFY_NOW",
    "EXECUTE_NOW",
    "IMPORT_NOW",
    "ACTIVATE_NOW",
)

REJECTION_REASONS: tuple[str, ...] = (
    "missing_evidence",
    "missing_approval",
    "frozen_file_must_not_be_modified",
    "no_cleanup_without_human_approval",
    "unknown_risk_class",
    "blocker_not_cleared",
)


@dataclass(frozen=True)
class CleanupDecision:
    """Single cleanup decision matrix entry."""
    decision_id: str
    path: str
    cleanup_classification: str
    decision: str
    decision_reason: str
    preconditions_met: bool
    evidence_sufficient: bool
    approval_obtained: bool
    blocker_cleared: bool
    would_archive: bool
    would_retain: bool
    would_review: bool
    would_reject: bool
    would_copy: bool
    would_move: bool
    would_delete: bool
    would_modify: bool
    simulation_only: bool
    human_approval_required: bool
    no_touch_required: bool
    advisory_only: bool

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "path": self.path,
            "cleanup_classification": self.cleanup_classification,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "preconditions_met": self.preconditions_met,
            "evidence_sufficient": self.evidence_sufficient,
            "approval_obtained": self.approval_obtained,
            "blocker_cleared": self.blocker_cleared,
            "would_archive": self.would_archive,
            "would_retain": self.would_retain,
            "would_review": self.would_review,
            "would_reject": self.would_reject,
            "would_copy": self.would_copy,
            "would_move": self.would_move,
            "would_delete": self.would_delete,
            "would_modify": self.would_modify,
            "simulation_only": self.simulation_only,
            "human_approval_required": self.human_approval_required,
            "no_touch_required": self.no_touch_required,
            "advisory_only": self.advisory_only,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def _evaluate_decision(item: dict) -> tuple[str, str, bool, bool, bool, bool]:
    """Evaluate cleanup decision for an inventory item.

    Returns: (decision, reason, preconditions_met, evidence_sufficient,
              approval_obtained, blocker_cleared)
    """
    classification = item.get("cleanup_classification", "REVIEW")
    has_evidence = item.get("has_required_evidence", False)
    has_approval = item.get("has_approval", False)
    risk_class = item.get("risk_class", "UNKNOWN")
    backup_status = item.get("backup_status", "PENDING")
    approval_status = item.get("approval_status", "PENDING")

    # High risk: always retain or review
    if risk_class == "HIGH":
        if has_approval and has_evidence:
            return ("REVIEW_REQUIRED", "high_risk_requires_explicit_review",
                    False, True, True, False)
        return ("RETAIN_FROZEN", "high_risk_retain_until_evidence_and_approval",
                False, has_evidence, has_approval, False)

    # No approval: retain or reject
    if not has_approval:
        if classification == "REJECT":
            return ("REJECT_FROM_CLEANUP", "rejected_no_approval_and_classification_reject",
                    False, has_evidence, False, True)
        return ("RETAIN_FROZEN", "no_approval_must_retain",
                False, has_evidence, False, False)

    # No evidence: retain
    if not has_evidence:
        return ("RETAIN_FROZEN", "evidence_insufficient_must_retain",
                False, False, True, False)

    # Classification-based decisions
    if classification == "ARCHIVE":
        return ("ARCHIVE_PROPOSED", "archive_proposed_pending_human_approval",
                True, True, True, True)
    if classification == "RETAIN":
        return ("RETAIN_FROZEN", "retain_as_frozen",
                True, True, True, True)
    if classification == "REVIEW":
        return ("REVIEW_REQUIRED", "requires_human_review_before_decision",
                False, True, True, False)
    if classification == "REJECT":
        return ("REJECT_FROM_CLEANUP", "rejected_by_classification",
                True, True, True, True)

    return ("REVIEW_REQUIRED", "unknown_classification",
            False, False, False, False)


def build_decision(item: dict) -> CleanupDecision:
    """Build a single cleanup decision from an inventory item."""
    path = item.get("path", "unknown")
    safe_id = _safe_id(path)
    classification = item.get("cleanup_classification", "REVIEW")

    decision, reason, preconds, evidence, approval, blocker = _evaluate_decision(item)

    would_archive = decision == "ARCHIVE_PROPOSED"
    would_retain = decision == "RETAIN_FROZEN"
    would_review = decision == "REVIEW_REQUIRED"
    would_reject = decision == "REJECT_FROM_CLEANUP"

    return CleanupDecision(
        decision_id=f"decision_{safe_id}",
        path=path,
        cleanup_classification=classification,
        decision=decision,
        decision_reason=reason,
        preconditions_met=preconds,
        evidence_sufficient=evidence,
        approval_obtained=approval,
        blocker_cleared=blocker,
        would_archive=would_archive,
        would_retain=would_retain,
        would_review=would_review,
        would_reject=would_reject,
        would_copy=False,
        would_move=False,
        would_delete=False,
        would_modify=False,
        simulation_only=True,
        human_approval_required=True,
        no_touch_required=True,
        advisory_only=True,
    )


def build_decision_matrix(
    inventory_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[CleanupDecision]:
    """Build full cleanup decision matrix from inventory items."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    return [build_decision(item) for item in inventory_items]


def compute_decision_hash(items: list[CleanupDecision]) -> str:
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_decision_matrix_markdown(items: list[CleanupDecision]) -> str:
    lines = [
        "# Frozen File Cleanup Decision Matrix",
        "",
        f"**Total decisions:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**simulation_only:** true for all items",
        "",
        "## Safety Boundary",
        "",
        "- would_copy: **false** for all items",
        "- would_move: **false** for all items",
        "- would_delete: **false** for all items",
        "- would_modify: **false** for all items",
        "- simulation_only: **true** for all items",
        "- human_approval_required: **true** for all items",
        "- no_touch_required: **true** for all items",
        "- advisory_only: **true** for all items",
        "",
        "## Decision Summary",
        "",
    ]

    decision_counts: dict[str, int] = {}
    for item in items:
        decision_counts[item.decision] = decision_counts.get(item.decision, 0) + 1
    for d, count in sorted(decision_counts.items()):
        lines.append(f"- **{d}:** {count}")

    lines.append("")
    lines.append("## Classification Summary")
    lines.append("")

    class_counts: dict[str, int] = {}
    for item in items:
        class_counts[item.cleanup_classification] = class_counts.get(item.cleanup_classification, 0) + 1
    for cls, count in sorted(class_counts.items()):
        lines.append(f"- **{cls}:** {count}")

    lines.append("")
    lines.append("## Decision Items")
    lines.append("")

    for item in items:
        lines.append(f"### {item.path}")
        lines.append("")
        lines.append(f"- **decision_id:** {item.decision_id}")
        lines.append(f"- **cleanup_classification:** {item.cleanup_classification}")
        lines.append(f"- **decision:** {item.decision}")
        lines.append(f"- **decision_reason:** {item.decision_reason}")
        lines.append(f"- **preconditions_met:** {item.preconditions_met}")
        lines.append(f"- **evidence_sufficient:** {item.evidence_sufficient}")
        lines.append(f"- **approval_obtained:** {item.approval_obtained}")
        lines.append(f"- **blocker_cleared:** {item.blocker_cleared}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def write_json(items: list[CleanupDecision], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(
    items: list[CleanupDecision],
    out_path,
    release_hold: str,
) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    decision_counts: dict[str, int] = {}
    for item in items:
        decision_counts[item.decision] = decision_counts.get(item.decision, 0) + 1
    manifest = {
        "total_items": len(items),
        "decision_counts": dict(sorted(decision_counts.items())),
        "release_hold": release_hold,
        "simulation_only": True,
        "would_copy": False,
        "would_move": False,
        "would_delete": False,
        "would_modify": False,
        "no_touch_required": True,
        "human_approval_required": True,
        "advisory_only": True,
        "decision_hash": compute_decision_hash(items),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[CleanupDecision], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_decision_matrix_markdown(items), encoding="utf-8")
