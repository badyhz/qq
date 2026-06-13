"""T25001 — Dangerous Runtime Isolator.

Pure deterministic. No I/O. No network.
Generates deny-list entries for all HIGH_RISK_* untracked files.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from core.untracked_runtime_inventory import (
    HIGH_RISK_CATEGORIES,
    UntrackedFileRecord,
    build_inventory,
    RELEASE_HOLD_REQUIRED,
)

RELEASE_HOLD_REQUIRED_ISO = "HOLD"

ISOLATION_ACTIONS: dict[str, tuple[str, ...]] = {
    "HIGH_RISK_TESTNET_SUBMIT": (
        "Add to execution deny-list",
        "Block all testnet order submissions",
        "Require human approval before any execution",
        "Add pre-commit hook to detect accidental imports",
    ),
    "HIGH_RISK_LIVE_RUNTIME": (
        "Add to execution deny-list",
        "Block all live trading paths",
        "Require human approval before any execution",
        "Add runtime guard to reject enable_live_trading=True",
    ),
    "HIGH_RISK_FLATTEN": (
        "Add to execution deny-list",
        "Block all flatten/reduce-only order paths",
        "Require human approval before any execution",
        "Add runtime guard to reject MARKET reduce-only orders",
    ),
    "HIGH_RISK_SECRET_OR_WEBHOOK": (
        "Quarantine file immediately",
        "Scan for embedded secrets",
        "Rotate any exposed credentials",
        "Require human security review before re-enable",
    ),
}

REQUIRED_UNBLOCK_CONDITIONS: dict[str, tuple[str, ...]] = {
    "HIGH_RISK_TESTNET_SUBMIT": (
        "Human signs off on testnet submit use case",
        "Execution guard integration verified",
        "Dry-run test passes with no real orders",
    ),
    "HIGH_RISK_LIVE_RUNTIME": (
        "Human signs off on live runtime use case",
        "Risk engine integration verified",
        "Deployment monitor integration verified",
        "Dry-run test passes with no real orders",
    ),
    "HIGH_RISK_FLATTEN": (
        "Human signs off on flatten use case",
        "Risk engine integration verified",
        "Execution guard integration verified",
        "Dry-run test passes with no real orders",
    ),
    "HIGH_RISK_SECRET_OR_WEBHOOK": (
        "Secret scan clean",
        "No embedded credentials found",
        "Human security review complete",
    ),
}


@dataclass(frozen=True)
class DenyListEntry:
    """Single deny-list entry for a dangerous file."""
    entry_id: str
    path: str
    risk_category: str
    risk_reason: str
    isolation_actions: tuple[str, ...]
    required_unblock_conditions: tuple[str, ...]
    human_approval_required: bool
    no_touch_required: bool
    isolation_status: str  # "ISOLATED" or "QUARANTINED"

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "path": self.path,
            "risk_category": self.risk_category,
            "risk_reason": self.risk_reason,
            "isolation_actions": list(self.isolation_actions),
            "required_unblock_conditions": list(self.required_unblock_conditions),
            "human_approval_required": self.human_approval_required,
            "no_touch_required": self.no_touch_required,
            "isolation_status": self.isolation_status,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def build_deny_list_entry(record: UntrackedFileRecord) -> DenyListEntry:
    """Build a deny-list entry from an inventory record."""
    actions = ISOLATION_ACTIONS.get(record.risk_category, ("Add to deny-list",))
    conditions = REQUIRED_UNBLOCK_CONDITIONS.get(record.risk_category, ("Human review required",))
    status = "QUARANTINED" if record.risk_category == "HIGH_RISK_SECRET_OR_WEBHOOK" else "ISOLATED"
    return DenyListEntry(
        entry_id=f"deny_{_safe_id(record.path)}",
        path=record.path,
        risk_category=record.risk_category,
        risk_reason=record.risk_reason,
        isolation_actions=actions,
        required_unblock_conditions=conditions,
        human_approval_required=True,
        no_touch_required=True,
        isolation_status=status,
    )


def build_deny_list(
    release_hold: str = RELEASE_HOLD_REQUIRED_ISO,
) -> list[DenyListEntry]:
    """Build deny-list for all high-risk files."""
    if release_hold != RELEASE_HOLD_REQUIRED_ISO:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    records = build_inventory(release_hold=RELEASE_HOLD_REQUIRED)
    return [
        build_deny_list_entry(r)
        for r in records
        if r.risk_category in HIGH_RISK_CATEGORIES
    ]


def compute_deny_list_hash(entries: list[DenyListEntry]) -> str:
    raw = json.dumps([e.to_dict() for e in entries], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_deny_list_markdown(entries: list[DenyListEntry]) -> str:
    lines = [
        "# Dangerous Runtime Deny List",
        "",
        f"**Total isolated files:** {len(entries)}",
        "",
        "## Isolation Summary",
        "",
    ]
    cat_counts: dict[str, int] = {}
    for e in entries:
        cat_counts[e.risk_category] = cat_counts.get(e.risk_category, 0) + 1
    for cat, count in sorted(cat_counts.items()):
        lines.append(f"- **{cat}:** {count}")

    lines.append("")
    lines.append("## Deny List Details")
    lines.append("")

    for e in entries:
        lines.append(f"### {e.path}")
        lines.append("")
        lines.append(f"- **Risk category:** {e.risk_category}")
        lines.append(f"- **Risk reason:** {e.risk_reason}")
        lines.append(f"- **Isolation status:** {e.isolation_status}")
        lines.append(f"- **Human approval required:** {e.human_approval_required}")
        lines.append(f"- **No touch required:** {e.no_touch_required}")
        lines.append("- **Isolation actions:**")
        for action in e.isolation_actions:
            lines.append(f"  - {action}")
        lines.append("- **Required unblock conditions:**")
        for cond in e.required_unblock_conditions:
            lines.append(f"  - {cond}")
        lines.append("")

    return "\n".join(lines)


def render_isolation_manifest_markdown(entries: list[DenyListEntry]) -> str:
    lines = [
        "# Isolation Manifest",
        "",
        "| File | Category | Status | Human Approval |",
        "|------|----------|--------|----------------|",
    ]
    for e in entries:
        lines.append(
            f"| {e.path} | {e.risk_category} | {e.isolation_status} | {e.human_approval_required} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_json(entries: list[DenyListEntry], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([e.to_dict() for e in entries], indent=2), encoding="utf-8")


def write_manifest(entries: list[DenyListEntry], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cat_counts: dict[str, int] = {}
    for e in entries:
        cat_counts[e.risk_category] = cat_counts.get(e.risk_category, 0) + 1
    manifest = {
        "total_isolated": len(entries),
        "category_counts": dict(sorted(cat_counts.items())),
        "release_hold": release_hold,
        "deny_list_hash": compute_deny_list_hash(entries),
        "all_require_human_approval": all(e.human_approval_required for e in entries),
        "all_no_touch": all(e.no_touch_required for e in entries),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
