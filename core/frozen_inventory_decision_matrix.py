"""Frozen inventory human decision matrix.

Turns frozen inventory audit records into a human disposition matrix.
Never imports, executes, stages, or modifies any frozen file.

release_hold = HOLD
advisory_only = True
no_live / no_submit / no_exchange / no_network = True
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

RELEASE_HOLD_REQUIRED = "HOLD"

DISPOSITION_CATEGORIES = [
    "KEEP_FROZEN",
    "NEEDS_HUMAN_REVIEW",
    "CANDIDATE_FOR_ARCHIVE",
    "CANDIDATE_FOR_REWRITE",
    "CANDIDATE_FOR_DELETION_AFTER_BACKUP",
    "UNKNOWN",
]

# Keywords that force NEEDS_HUMAN_REVIEW
HUMAN_REVIEW_KEYWORDS = [
    "live", "submit", "order", "cancel", "flatten",
    "testnet", "runtime", "fapi", "binance",
]

# Keywords that force CANDIDATE_FOR_REWRITE or CANDIDATE_FOR_ARCHIVE
HIGH_RISK_KEYWORDS = ["flatten", "cancel", "submit"]

FORBIDDEN_MARKERS = [
    "APPROVED", "SAFE_TO_EXECUTE", "SAFE_TO_IMPORT",
    "SAFE_TO_STAGE", "ACTIVATE", "ENABLE_LIVE",
]


@dataclass
class DecisionEntry:
    path: str
    exists: bool
    status: str
    category: str
    risk_keywords: list[str] = field(default_factory=list)
    risk_score: int = 0
    disposition: str = "UNKNOWN"
    disposition_reason: str = ""
    required_human_action: str = ""
    allowed_agent_action: str = "none"
    forbidden_agent_action: str = "execute, import, stage, modify, delete, rename"
    no_execution: bool = True
    no_import: bool = True
    no_stage: bool = True
    release_hold: str = "HOLD"
    advisory_only: bool = True
    human_review_required: bool = True


@dataclass
class DecisionMatrix:
    entries: list[DecisionEntry]
    manifest: dict[str, Any]


def _compute_risk_score(risk_keywords: list[str], category: str) -> int:
    score = 0
    for kw in risk_keywords:
        if kw in HIGH_RISK_KEYWORDS:
            score += 10
        elif kw in HUMAN_REVIEW_KEYWORDS:
            score += 5
        else:
            score += 1
    if category in ("LIVE", "SUBMIT", "FLATTEN", "CANCEL"):
        score += 20
    elif category in ("TESTNET", "RUNTIME"):
        score += 15
    elif category in ("SHADOW", "OBSERVATION"):
        score += 10
    return score


def _determine_disposition(
    risk_keywords: list[str],
    category: str,
    risk_score: int,
) -> tuple[str, str]:
    """Return (disposition, reason)."""
    combined = set(k.lower() for k in risk_keywords)

    # Flatten/cancel/submit -> rewrite or archive, never safe
    if any(k in combined for k in ("flatten", "cancel")):
        return "CANDIDATE_FOR_REWRITE", "contains cancel/flatten operations"
    if "submit" in combined:
        return "CANDIDATE_FOR_ARCHIVE", "contains submit operations"

    # Live/testnet/runtime/fapi/binance -> needs human review
    if any(k in combined for k in HUMAN_REVIEW_KEYWORDS):
        return "NEEDS_HUMAN_REVIEW", f"risk keywords: {sorted(combined & set(HUMAN_REVIEW_KEYWORDS))}"

    # Unknown category -> needs human review
    if category == "UNKNOWN":
        return "NEEDS_HUMAN_REVIEW", "UNKNOWN category requires human review"

    # High risk score
    if risk_score >= 15:
        return "NEEDS_HUMAN_REVIEW", f"high risk score: {risk_score}"

    # Archive candidate
    if risk_score >= 5:
        return "CANDIDATE_FOR_ARCHIVE", f"moderate risk score: {risk_score}"

    # Low risk
    if risk_score > 0:
        return "KEEP_FROZEN", f"low risk score: {risk_score}"

    # No risk detected
    return "KEEP_FROZEN", "no risk keywords detected"


def _determine_human_action(disposition: str, risk_score: int) -> str:
    if disposition == "NEEDS_HUMAN_REVIEW":
        return "Human must review and decide disposition before any action"
    if disposition == "CANDIDATE_FOR_REWRITE":
        return "Human must approve rewrite scope and review rewritten version"
    if disposition == "CANDIDATE_FOR_ARCHIVE":
        return "Human must approve archive target and verify no live dependencies"
    if disposition == "CANDIDATE_FOR_DELETION_AFTER_BACKUP":
        return "Human must approve backup verification before deletion"
    if disposition == "KEEP_FROZEN":
        return "No action required — remain frozen"
    return "Human must review and decide"


def build_decision_matrix(inventory_data: dict[str, Any]) -> DecisionMatrix:
    """Build decision matrix from frozen inventory JSON data."""
    entries: list[DecisionEntry] = []

    for file_rec in inventory_data.get("files", []):
        path = file_rec.get("path", "")
        exists = file_rec.get("exists", False)
        git_status = file_rec.get("git_status", "unknown")
        risk_keywords = file_rec.get("risk_keywords", [])
        category = file_rec.get("category", "UNKNOWN")

        risk_score = _compute_risk_score(risk_keywords, category)
        disposition, reason = _determine_disposition(risk_keywords, category, risk_score)
        human_action = _determine_human_action(disposition, risk_score)

        entry = DecisionEntry(
            path=path,
            exists=exists,
            status=git_status,
            category=category,
            risk_keywords=sorted(risk_keywords),
            risk_score=risk_score,
            disposition=disposition,
            disposition_reason=reason,
            required_human_action=human_action,
            allowed_agent_action="none",
            forbidden_agent_action="execute, import, stage, modify, delete, rename",
            no_execution=True,
            no_import=True,
            no_stage=True,
            release_hold="HOLD",
            advisory_only=True,
            human_review_required=True,
        )
        entries.append(entry)

    manifest = _build_manifest(entries)
    return DecisionMatrix(entries=entries, manifest=manifest)


def _build_manifest(entries: list[DecisionEntry]) -> dict[str, Any]:
    cat_counts: dict[str, int] = {}
    disp_counts: dict[str, int] = {}
    for e in entries:
        cat_counts[e.category] = cat_counts.get(e.category, 0) + 1
        disp_counts[e.disposition] = disp_counts.get(e.disposition, 0) + 1

    return {
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_execution": True,
        "no_import": True,
        "no_stage": True,
        "no_approved": True,
        "no_safe_to_execute": True,
        "no_safe_to_import": True,
        "generated_by": "frozen_inventory_decision_matrix.py",
        "total_entries": len(entries),
        "category_counts": cat_counts,
        "disposition_counts": disp_counts,
    }


def validate_no_forbidden_markers(matrix: DecisionMatrix) -> list[str]:
    """Check that no entry contains forbidden approval markers."""
    violations: list[str] = []
    for entry in matrix.entries:
        for marker in FORBIDDEN_MARKERS:
            if marker.lower() in entry.disposition.lower():
                violations.append(f"{entry.path}: disposition contains {marker}")
            if marker.lower() in entry.required_human_action.lower():
                violations.append(f"{entry.path}: human_action contains {marker}")
    return violations


def validate_release_hold(matrix: DecisionMatrix, release_hold: str) -> bool:
    return release_hold == RELEASE_HOLD_REQUIRED


def write_json(matrix: DecisionMatrix, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "manifest": matrix.manifest,
        "entries": [_entry_to_dict(e) for e in matrix.entries],
    }
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(matrix: DecisionMatrix, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(matrix.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(matrix: DecisionMatrix, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Frozen Inventory Human Decision Matrix")
    lines.append("")
    lines.append(f"**release_hold:** {matrix.manifest['release_hold']}")
    lines.append(f"**advisory_only:** {matrix.manifest['advisory_only']}")
    lines.append(f"**human_review_required:** {matrix.manifest['human_review_required']}")
    lines.append(f"**total entries:** {len(matrix.entries)}")
    lines.append("")

    lines.append("## Disposition Summary")
    lines.append("")
    for disp, count in sorted(matrix.manifest["disposition_counts"].items()):
        lines.append(f"- {disp}: {count}")
    lines.append("")

    lines.append("## Decision Matrix")
    lines.append("")
    lines.append("| Path | Category | Risk Score | Disposition | Reason |")
    lines.append("|------|----------|------------|-------------|--------|")
    for e in matrix.entries:
        lines.append(f"| {e.path} | {e.category} | {e.risk_score} | {e.disposition} | {e.disposition_reason} |")
    lines.append("")

    lines.append("## Required Human Actions")
    lines.append("")
    for e in matrix.entries:
        if e.disposition != "KEEP_FROZEN":
            lines.append(f"- **{e.path}**: {e.required_human_action}")
    lines.append("")

    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No file marked APPROVED")
    lines.append("- No file marked SAFE_TO_EXECUTE")
    lines.append("- No file marked SAFE_TO_IMPORT")
    lines.append("- release_hold = HOLD")
    lines.append("- Advisory only. Human review required.")
    lines.append("- No execution. No import. No staging.")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _entry_to_dict(entry: DecisionEntry) -> dict[str, Any]:
    return {
        "path": entry.path,
        "exists": entry.exists,
        "status": entry.status,
        "category": entry.category,
        "risk_keywords": entry.risk_keywords,
        "risk_score": entry.risk_score,
        "disposition": entry.disposition,
        "disposition_reason": entry.disposition_reason,
        "required_human_action": entry.required_human_action,
        "allowed_agent_action": entry.allowed_agent_action,
        "forbidden_agent_action": entry.forbidden_agent_action,
        "no_execution": entry.no_execution,
        "no_import": entry.no_import,
        "no_stage": entry.no_stage,
        "release_hold": entry.release_hold,
        "advisory_only": entry.advisory_only,
        "human_review_required": entry.human_review_required,
    }
