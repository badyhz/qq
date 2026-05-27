"""Runtime governance closeout checklist — pre-live closeout verification.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceCloseoutChecklistItem:
    """Single closeout checklist item."""

    item_id: str
    description: str
    status: str  # "PASS" / "WARN" / "FAIL"


@dataclass(frozen=True)
class RuntimeGovernanceCloseoutChecklist:
    """Immutable closeout checklist for runtime governance."""

    title: str
    items: List[RuntimeGovernanceCloseoutChecklistItem]
    verdict: str  # "PASS" / "WARN" / "FAIL"
    notes: List[str] = field(default_factory=list)


_DEFAULT_ITEMS: List[Dict[str, str]] = [
    {"item_id": "C1", "description": "all_tests_passing", "status": "PASS"},
    {"item_id": "C2", "description": "no_hardcoded_secrets", "status": "PASS"},
    {"item_id": "C3", "description": "dry_run_default", "status": "PASS"},
    {"item_id": "C4", "description": "risk_controls_verified", "status": "PASS"},
    {"item_id": "C5", "description": "documentation_complete", "status": "PASS"},
]


def build_runtime_governance_closeout_checklist(
    *,
    title: str = "Runtime Governance Closeout Checklist",
    items: List[RuntimeGovernanceCloseoutChecklistItem] | None = None,
    verdict: str | None = None,
    notes: List[str] | None = None,
) -> RuntimeGovernanceCloseoutChecklist:
    """Build closeout checklist. Pure. No I/O.

    Defaults produce a checklist with all items passing (PASS).
    """
    if items is None:
        items = [
            RuntimeGovernanceCloseoutChecklistItem(**spec)
            for spec in _DEFAULT_ITEMS
        ]

    eff_verdict = verdict if verdict is not None else _compute_verdict(items)

    return RuntimeGovernanceCloseoutChecklist(
        title=title,
        items=items,
        verdict=eff_verdict,
        notes=list(notes) if notes else [],
    )


def summarize_closeout_checklist(checklist: RuntimeGovernanceCloseoutChecklist) -> Dict[str, Any]:
    """Summarize closeout checklist counts. Deterministic."""
    by_status: Dict[str, int] = {}
    for item in checklist.items:
        by_status[item.status] = by_status.get(item.status, 0) + 1

    return {
        "total": len(checklist.items),
        "by_status": dict(sorted(by_status.items())),
        "verdict": checklist.verdict,
    }


def closeout_checklist_to_dict(checklist: RuntimeGovernanceCloseoutChecklist) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "title": checklist.title,
        "items": [
            {
                "item_id": item.item_id,
                "description": item.description,
                "status": item.status,
            }
            for item in checklist.items
        ],
        "verdict": checklist.verdict,
        "notes": list(checklist.notes),
    }


def closeout_checklist_to_markdown(checklist: RuntimeGovernanceCloseoutChecklist) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines: List[str] = [f"# {checklist.title}", ""]
    lines.append(f"**Verdict:** {checklist.verdict}")
    lines.append("")
    lines.append("| Item | Description | Status |")
    lines.append("|------|-------------|--------|")
    for item in checklist.items:
        lines.append(f"| {item.item_id} | {item.description} | {item.status} |")
    lines.append("")
    if checklist.notes:
        lines.append("## Notes")
        lines.append("")
        for note in checklist.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


# ── internal ───────────────────────────────────────────────────────


def _compute_verdict(items: List[RuntimeGovernanceCloseoutChecklistItem]) -> str:
    has_fail = any(item.status == "FAIL" for item in items)
    has_warn = any(item.status == "WARN" for item in items)
    if has_fail:
        return "FAIL"
    if has_warn:
        return "WARN"
    return "PASS"
