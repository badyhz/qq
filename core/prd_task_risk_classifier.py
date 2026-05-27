"""PRD task risk classifier. Pure, deterministic, no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class PrdTaskRiskClassification:
    task_id: str
    risk_level: str
    reasons: List[str]
    recommended_controls: List[str]
    allowed_for_agent: bool


# Keyword sets per level (checked in order: FROZEN > HIGH > MEDIUM > LOW)
_FROZEN_KEYWORDS = [
    "live trading",
    "real submit",
    "secrets",
    "api key",
    "exchange client",
    "account mutation",
    "planner autonomous",
]

_HIGH_KEYWORDS = [
    "runtime integration",
    "hook implementation",
    "file writer",
    "cli execution",
    "network",
]

_MEDIUM_KEYWORDS = [
    "validator",
    "parser",
    "prompt generator",
    "dependency graph",
]


def _match_keywords(text: str, keywords: List[str]) -> List[str]:
    """Return which keywords appear in text (case-insensitive)."""
    lower = text.lower()
    return [kw for kw in keywords if kw in lower]


def classify_prd_task_risk(
    task_id: str,
    title: str,
    notes: List[str],
    allowed_files: List[str],
) -> PrdTaskRiskClassification:
    """Classify risk from task metadata. Pure and deterministic."""
    combined = title + " " + " ".join(notes) + " " + " ".join(allowed_files)
    combined_lower = combined.lower()

    # FROZEN
    frozen_hits = _match_keywords(combined_lower, _FROZEN_KEYWORDS)
    if frozen_hits:
        return PrdTaskRiskClassification(
            task_id=task_id,
            risk_level="FROZEN",
            reasons=[f"Contains forbidden keyword: {kw}" for kw in frozen_hits],
            recommended_controls=["block_execution", "require_human_review"],
            allowed_for_agent=False,
        )

    # HIGH
    high_hits = _match_keywords(combined_lower, _HIGH_KEYWORDS)
    if high_hits:
        return PrdTaskRiskClassification(
            task_id=task_id,
            risk_level="HIGH",
            reasons=[f"Contains high-risk keyword: {kw}" for kw in high_hits],
            recommended_controls=["require_dry_run", "require_review_before_merge"],
            allowed_for_agent=True,
        )

    # MEDIUM
    medium_hits = _match_keywords(combined_lower, _MEDIUM_KEYWORDS)
    if medium_hits:
        return PrdTaskRiskClassification(
            task_id=task_id,
            risk_level="MEDIUM",
            reasons=[f"Contains medium-risk keyword: {kw}" for kw in medium_hits],
            recommended_controls=["require_tests_pass"],
            allowed_for_agent=True,
        )

    # LOW (default)
    return PrdTaskRiskClassification(
        task_id=task_id,
        risk_level="LOW",
        reasons=["Docs, tests, or static report only"],
        recommended_controls=[],
        allowed_for_agent=True,
    )


def classify_backlog_item_risk(item: Any) -> PrdTaskRiskClassification:
    """Classify a backlog item (dict or object with expected attrs)."""
    if isinstance(item, dict):
        task_id = item.get("task_id", item.get("id", "unknown"))
        title = item.get("title", "")
        notes = item.get("notes", [])
        allowed_files = item.get("allowed_files", [])
    else:
        task_id = getattr(item, "task_id", getattr(item, "id", "unknown"))
        title = getattr(item, "title", "")
        notes = getattr(item, "notes", [])
        allowed_files = getattr(item, "allowed_files", [])
    return classify_prd_task_risk(task_id, title, notes, allowed_files)


def risk_classification_to_dict(c: PrdTaskRiskClassification) -> Dict[str, Any]:
    """Convert classification to plain dict."""
    return {
        "task_id": c.task_id,
        "risk_level": c.risk_level,
        "reasons": list(c.reasons),
        "recommended_controls": list(c.recommended_controls),
        "allowed_for_agent": c.allowed_for_agent,
    }


def risk_classification_to_markdown(c: PrdTaskRiskClassification) -> str:
    """Convert classification to markdown string."""
    lines = [
        f"## Risk Classification: {c.task_id}",
        "",
        f"- **Risk Level:** {c.risk_level}",
        f"- **Allowed for Agent:** {'yes' if c.allowed_for_agent else 'no'}",
        "",
        "### Reasons",
    ]
    for r in c.reasons:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("### Recommended Controls")
    if c.recommended_controls:
        for ctrl in c.recommended_controls:
            lines.append(f"- {ctrl}")
    else:
        lines.append("- (none)")
    return "\n".join(lines)
