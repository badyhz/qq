"""T15001 — Frozen Human Review Queue builder.

Pure deterministic. No I/O. No network. No execution.
Reads decision matrix entries, assigns priority, produces queue items.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

RELEASE_HOLD_REQUIRED = "HOLD"

# --- Priority classification keywords ---
_P0_KEYWORDS = frozenset([
    "submit", "cancel", "flatten", "live", "runtime", "binance", "fapi",
])
_P1_KEYWORDS = frozenset([
    "testnet", "order", "positionrisk", "exchange",
])
_P2_KEYWORDS = frozenset([
    "shadow", "observation", "verify",
])

POSSIBLE_DECISIONS: tuple[str, ...] = (
    "KEEP_FROZEN",
    "ARCHIVE_AFTER_BACKUP",
    "REWRITE_OFFLINE_ONLY",
    "DELETE_AFTER_BACKUP",
    "NEEDS_MORE_REVIEW",
)

FORBIDDEN_DECISIONS: tuple[str, ...] = (
    "EXECUTE",
    "IMPORT",
    "ACTIVATE_LIVE",
    "ACTIVATE_TESTNET",
    "ENABLE_RUNTIME",
    "ENABLE_PLANNER",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
    "APPROVE_WITHOUT_BACKUP",
)

REVIEWER_ROLES: dict[str, str] = {
    "P0_CRITICAL_REVIEW": "senior_operator",
    "P1_HIGH_REVIEW": "operator",
    "P2_STANDARD_REVIEW": "reviewer",
    "P3_LOW_REVIEW": "reviewer",
    "UNKNOWN_REVIEW": "operator",
}


@dataclass(frozen=True)
class QueueItem:
    """Single human review queue entry."""
    queue_id: str
    path: str
    exists: bool
    category: str
    risk_score: int
    risk_keywords: tuple[str, ...]
    disposition: str
    priority: str
    reviewer_role: str
    required_questions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    possible_decisions: tuple[str, ...]
    forbidden_decisions: tuple[str, ...]
    recommended_default_action: str
    no_touch_required: bool
    no_execution: bool
    no_import: bool
    no_stage: bool
    release_hold: str
    advisory_only: bool
    human_review_required: bool

    def to_dict(self) -> dict:
        return {
            "queue_id": self.queue_id,
            "path": self.path,
            "exists": self.exists,
            "category": self.category,
            "risk_score": self.risk_score,
            "risk_keywords": list(self.risk_keywords),
            "disposition": self.disposition,
            "priority": self.priority,
            "reviewer_role": self.reviewer_role,
            "required_questions": list(self.required_questions),
            "required_evidence": list(self.required_evidence),
            "possible_decisions": list(self.possible_decisions),
            "forbidden_decisions": list(self.forbidden_decisions),
            "recommended_default_action": self.recommended_default_action,
            "no_touch_required": self.no_touch_required,
            "no_execution": self.no_execution,
            "no_import": self.no_import,
            "no_stage": self.no_stage,
            "release_hold": self.release_hold,
            "advisory_only": self.advisory_only,
            "human_review_required": self.human_review_required,
        }


def classify_priority(risk_keywords: list[str], category: str) -> str:
    """Determine priority from risk keywords and category."""
    kw_lower = {k.lower() for k in risk_keywords}
    cat_lower = category.lower()
    combined = kw_lower | {cat_lower}
    if combined & _P0_KEYWORDS:
        return "P0_CRITICAL_REVIEW"
    if combined & _P1_KEYWORDS:
        return "P1_HIGH_REVIEW"
    if combined & _P2_KEYWORDS:
        return "P2_STANDARD_REVIEW"
    if category == "UNKNOWN" and not kw_lower:
        return "UNKNOWN_REVIEW"
    return "P3_LOW_REVIEW"


def _build_required_questions(priority: str, path: str, disposition: str) -> list[str]:
    questions = [
        f"Is {path} still needed for any purpose?",
        f"Does {path} contain secrets or credentials?",
    ]
    if priority in ("P0_CRITICAL_REVIEW", "P1_HIGH_REVIEW"):
        questions.append(f"Has {path} been reviewed for live/testnet safety?")
        questions.append("Is a backup verified before any action?")
    if disposition in ("CANDIDATE_FOR_REWRITE",):
        questions.append("What is the offline-only rewrite scope?")
    if disposition in ("CANDIDATE_FOR_ARCHIVE",):
        questions.append("Is archive evidence complete?")
    return questions


def _build_required_evidence(priority: str, disposition: str) -> list[str]:
    evidence = ["file_hash_snapshot"]
    if priority in ("P0_CRITICAL_REVIEW", "P1_HIGH_REVIEW"):
        evidence.append("owner_review_signoff")
        evidence.append("backup_verification")
    if disposition in ("CANDIDATE_FOR_ARCHIVE", "CANDIDATE_FOR_REWRITE"):
        evidence.append("diff_review_of_proposed_changes")
    return evidence


def _default_action(disposition: str) -> str:
    mapping = {
        "CANDIDATE_FOR_ARCHIVE": "KEEP_FROZEN",
        "CANDIDATE_FOR_REWRITE": "KEEP_FROZEN",
        "CANDIDATE_FOR_DELETE": "KEEP_FROZEN",
        "NEEDS_HUMAN_REVIEW": "NEEDS_MORE_REVIEW",
    }
    return mapping.get(disposition, "KEEP_FROZEN")


def build_queue_item(idx: int, entry: dict, release_hold: str) -> QueueItem:
    """Build a single QueueItem from a decision matrix entry."""
    risk_keywords = entry.get("risk_keywords", [])
    category = entry.get("category", "UNKNOWN")
    disposition = entry.get("disposition", "NEEDS_HUMAN_REVIEW")
    priority = classify_priority(risk_keywords, category)
    reviewer_role = REVIEWER_ROLES.get(priority, "operator")

    return QueueItem(
        queue_id=f"QR-{idx + 1:04d}",
        path=entry["path"],
        exists=entry.get("exists", True),
        category=category,
        risk_score=entry.get("risk_score", 0),
        risk_keywords=tuple(risk_keywords),
        disposition=disposition,
        priority=priority,
        reviewer_role=reviewer_role,
        required_questions=_build_required_questions(priority, entry["path"], disposition),
        required_evidence=_build_required_evidence(priority, disposition),
        possible_decisions=list(POSSIBLE_DECISIONS),
        forbidden_decisions=list(FORBIDDEN_DECISIONS),
        recommended_default_action=_default_action(disposition),
        no_touch_required=True,
        no_execution=True,
        no_import=True,
        no_stage=True,
        release_hold=release_hold,
        advisory_only=True,
        human_review_required=True,
    )


def build_queue_from_matrix(
    entries: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[QueueItem]:
    """Build full queue from decision matrix entries."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    return [build_queue_item(i, e, release_hold) for i, e in enumerate(entries)]


def render_queue_markdown(items: list[QueueItem]) -> str:
    """Render queue as markdown."""
    lines = [
        "# Frozen File Human Review Queue",
        "",
        f"**Total items:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**advisory_only:** true",
        f"**human_review_required:** true",
        "",
        "## Priority Summary",
        "",
    ]
    counts: dict[str, int] = {}
    for item in items:
        counts[item.priority] = counts.get(item.priority, 0) + 1
    for p in ("P0_CRITICAL_REVIEW", "P1_HIGH_REVIEW", "P2_STANDARD_REVIEW", "P3_LOW_REVIEW", "UNKNOWN_REVIEW"):
        if p in counts:
            lines.append(f"- **{p}:** {counts[p]}")
    lines.append("")
    lines.append("## No-Touch Statement")
    lines.append("")
    lines.append("All frozen files require explicit human review and approval before any action.")
    lines.append("No file may be executed, imported, staged, moved, deleted, or renamed without approval.")
    lines.append("")
    lines.append("## Queue Items")
    lines.append("")

    for item in items:
        lines.append(f"### {item.queue_id}: {item.path}")
        lines.append("")
        lines.append(f"- **Priority:** {item.priority}")
        lines.append(f"- **Category:** {item.category}")
        lines.append(f"- **Risk Score:** {item.risk_score}")
        lines.append(f"- **Risk Keywords:** {', '.join(item.risk_keywords)}")
        lines.append(f"- **Disposition:** {item.disposition}")
        lines.append(f"- **Reviewer Role:** {item.reviewer_role}")
        lines.append(f"- **Recommended Default:** {item.recommended_default_action}")
        lines.append(f"- **Possible Decisions:** {', '.join(item.possible_decisions)}")
        lines.append(f"- **Forbidden Decisions:** {', '.join(item.forbidden_decisions)}")
        lines.append("")
        lines.append("**Required Questions:**")
        for q in item.required_questions:
            lines.append(f"  - {q}")
        lines.append("")
        lines.append("**Required Evidence:**")
        for e in item.required_evidence:
            lines.append(f"  - {e}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def load_decision_matrix(path: pathlib.Path) -> list[dict]:
    """Load entries from decision_matrix.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data.get("entries", [])
    return data


def write_json(items: list[QueueItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(items: list[QueueItem], out_path: pathlib.Path, release_hold: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "total_items": len(items),
        "priority_counts": {},
        "release_hold": release_hold,
        "advisory_only": True,
        "human_review_required": True,
        "no_touch_required": True,
    }
    for item in items:
        manifest["priority_counts"][item.priority] = (
            manifest["priority_counts"].get(item.priority, 0) + 1
        )
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[QueueItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_queue_markdown(items), encoding="utf-8")
