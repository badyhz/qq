"""T17001 — Frozen File Final Inventory.

Pure deterministic. No I/O. No network. No actual file operations.
Aggregates all frozen file sources into a unified final inventory.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_CATEGORIES: tuple[str, ...] = (
    "LIVE_RUNNER",
    "LIVE_PLAYBOOK",
    "SUBMIT",
    "TESTNET_SMOKE",
    "FLATTEN",
    "REPLAY_SUBMIT",
    "OPERATIONAL_SHADOW",
    "VERIFICATION",
    "UNTRACKED_SCRIPT",
    "EXTERNAL_DOC",
    "RESEARCH_ARTIFACT",
    "FROZEN_CORE",
)

VALID_CLEANUP_CLASSIFICATIONS: tuple[str, ...] = (
    "ARCHIVE",
    "RETAIN",
    "REVIEW",
    "REJECT",
)

FORBIDDEN_CLEANUP_ACTIONS: tuple[str, ...] = (
    "DELETE_NOW",
    "MOVE_NOW",
    "MODIFY_NOW",
    "EXECUTE_NOW",
    "IMPORT_NOW",
    "ACTIVATE_NOW",
)


@dataclass(frozen=True)
class FrozenCleanupInventoryItem:
    """Single frozen file in final cleanup inventory."""
    item_id: str
    path: str
    source: str
    risk_class: str
    category: str
    cleanup_classification: str
    classification_reason: str
    has_required_evidence: bool
    has_approval: bool
    is_tracked_in_backlog: bool
    is_untracked: bool
    is_external: bool
    backup_status: str
    archive_simulation_status: str
    approval_status: str
    no_touch_required: bool
    simulation_only: bool
    human_approval_required: bool
    would_copy: bool
    would_move: bool
    would_delete: bool
    would_modify: bool

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "path": self.path,
            "source": self.source,
            "risk_class": self.risk_class,
            "category": self.category,
            "cleanup_classification": self.cleanup_classification,
            "classification_reason": self.classification_reason,
            "has_required_evidence": self.has_required_evidence,
            "has_approval": self.has_approval,
            "is_tracked_in_backlog": self.is_tracked_in_backlog,
            "is_untracked": self.is_untracked,
            "is_external": self.is_external,
            "backup_status": self.backup_status,
            "archive_simulation_status": self.archive_simulation_status,
            "approval_status": self.approval_status,
            "no_touch_required": self.no_touch_required,
            "simulation_only": self.simulation_only,
            "human_approval_required": self.human_approval_required,
            "would_copy": self.would_copy,
            "would_move": self.would_move,
            "would_delete": self.would_delete,
            "would_modify": self.would_modify,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def _classify_backlog_item(record: dict) -> tuple[str, str]:
    """Classify a tracked frozen backlog item."""
    risk = record.get("risk_class", "UNKNOWN")
    category = record.get("category", "UNKNOWN")
    evidence = record.get("required_evidence", ())
    approval = record.get("unlock_recommendation", "HOLD")

    if risk == "HIGH" and approval == "HOLD":
        return "RETAIN", "high_risk_frozen_awaiting_approval"
    if risk == "HIGH":
        return "REVIEW", "high_risk_needs_review_before_any_action"
    if category in ("OPERATIONAL_SHADOW", "VERIFICATION"):
        return "RETAIN", "operational_shadow_or_verification_keep_frozen"
    if category == "SUBMIT":
        return "REVIEW", "submit_category_requires_explicit_review"
    return "RETAIN", "default_retain_pending_evidence"


def _classify_untracked(path: str) -> tuple[str, str]:
    """Classify an untracked file."""
    if path.endswith(".py"):
        return "REVIEW", "untracked_python_requires_review"
    if path.endswith(".md"):
        return "REVIEW", "untracked_markdown_requires_review"
    if path.endswith(".json"):
        return "REVIEW", "untracked_json_requires_review"
    return "REVIEW", "untracked_file_requires_review"


def _classify_external(path: str) -> tuple[str, str]:
    """Classify an external/research artifact."""
    if "research/" in path:
        return "RETAIN", "research_artifact_retain_offline"
    if path.endswith(".md"):
        return "RETAIN", "documentation_retain"
    return "REVIEW", "external_artifact_requires_review"


def build_inventory_item_from_backlog(
    record: dict,
    source: str = "backlog_inventory",
) -> FrozenCleanupInventoryItem:
    """Build inventory item from a frozen backlog record."""
    path = record.get("file_path", record.get("path", "unknown"))
    safe_id = _safe_id(path)
    classification, reason = _classify_backlog_item(record)

    return FrozenCleanupInventoryItem(
        item_id=f"cleanup_{safe_id}",
        path=path,
        source=source,
        risk_class=record.get("risk_class", "UNKNOWN"),
        category=record.get("category", "UNKNOWN"),
        cleanup_classification=classification,
        classification_reason=reason,
        has_required_evidence=False,
        has_approval=False,
        is_tracked_in_backlog=True,
        is_untracked=False,
        is_external=False,
        backup_status="PENDING",
        archive_simulation_status="PENDING",
        approval_status="PENDING",
        no_touch_required=True,
        simulation_only=True,
        human_approval_required=True,
        would_copy=False,
        would_move=False,
        would_delete=False,
        would_modify=False,
    )


def build_inventory_item_from_untracked(
    path: str,
) -> FrozenCleanupInventoryItem:
    """Build inventory item from an untracked frozen-related file."""
    safe_id = _safe_id(path)
    classification, reason = _classify_untracked(path)

    return FrozenCleanupInventoryItem(
        item_id=f"cleanup_{safe_id}",
        path=path,
        source="git_untracked",
        risk_class="UNKNOWN",
        category="UNTRACKED_SCRIPT",
        cleanup_classification=classification,
        classification_reason=reason,
        has_required_evidence=False,
        has_approval=False,
        is_tracked_in_backlog=False,
        is_untracked=True,
        is_external=False,
        backup_status="NOT_APPLICABLE",
        archive_simulation_status="NOT_APPLICABLE",
        approval_status="PENDING",
        no_touch_required=True,
        simulation_only=True,
        human_approval_required=True,
        would_copy=False,
        would_move=False,
        would_delete=False,
        would_modify=False,
    )


def build_inventory_item_from_external(
    path: str,
    category: str = "EXTERNAL_DOC",
) -> FrozenCleanupInventoryItem:
    """Build inventory item from an external/research artifact."""
    safe_id = _safe_id(path)
    classification, reason = _classify_external(path)

    return FrozenCleanupInventoryItem(
        item_id=f"cleanup_{safe_id}",
        path=path,
        source="external_artifact",
        risk_class="LOW",
        category=category,
        cleanup_classification=classification,
        classification_reason=reason,
        has_required_evidence=False,
        has_approval=False,
        is_tracked_in_backlog=False,
        is_untracked=False,
        is_external=True,
        backup_status="NOT_APPLICABLE",
        archive_simulation_status="NOT_APPLICABLE",
        approval_status="PENDING",
        no_touch_required=True,
        simulation_only=True,
        human_approval_required=True,
        would_copy=False,
        would_move=False,
        would_delete=False,
        would_modify=False,
    )


def build_final_inventory(
    backlog_records: list[dict],
    untracked_paths: list[str],
    external_paths: list[str],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[FrozenCleanupInventoryItem]:
    """Build final cleanup inventory from all sources."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    items: list[FrozenCleanupInventoryItem] = []
    seen_paths: set[str] = set()

    for rec in backlog_records:
        path = rec.get("file_path", rec.get("path", ""))
        if path and path not in seen_paths:
            items.append(build_inventory_item_from_backlog(rec))
            seen_paths.add(path)

    for path in untracked_paths:
        if path and path not in seen_paths:
            items.append(build_inventory_item_from_untracked(path))
            seen_paths.add(path)

    for path in external_paths:
        if path and path not in seen_paths:
            items.append(build_inventory_item_from_external(path))
            seen_paths.add(path)

    return items


def compute_inventory_hash(items: list[FrozenCleanupInventoryItem]) -> str:
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_inventory_markdown(items: list[FrozenCleanupInventoryItem]) -> str:
    lines = [
        "# Frozen File Final Cleanup Inventory",
        "",
        f"**Total items:** {len(items)}",
        f"**release_hold:** HOLD",
        f"**simulation_only:** true for all items",
        "",
        "## Safety Boundary",
        "",
        "- would_copy: **false** for all items",
        "- would_move: **false** for all items",
        "- would_delete: **false** for all items",
        "- would_modify: **false** for all items",
        "- no_touch_required: **true** for all items",
        "- human_approval_required: **true** for all items",
        "",
        "## Classification Summary",
        "",
    ]

    class_counts: dict[str, int] = {}
    for item in items:
        class_counts[item.cleanup_classification] = class_counts.get(item.cleanup_classification, 0) + 1
    for cls, count in sorted(class_counts.items()):
        lines.append(f"- **{cls}:** {count}")

    lines.append("")
    lines.append("## Source Summary")
    lines.append("")

    source_counts: dict[str, int] = {}
    for item in items:
        source_counts[item.source] = source_counts.get(item.source, 0) + 1
    for src, count in sorted(source_counts.items()):
        lines.append(f"- **{src}:** {count}")

    lines.append("")
    lines.append("## Inventory Items")
    lines.append("")

    for item in items:
        lines.append(f"### {item.path}")
        lines.append("")
        lines.append(f"- **item_id:** {item.item_id}")
        lines.append(f"- **source:** {item.source}")
        lines.append(f"- **risk_class:** {item.risk_class}")
        lines.append(f"- **category:** {item.category}")
        lines.append(f"- **cleanup_classification:** {item.cleanup_classification}")
        lines.append(f"- **classification_reason:** {item.classification_reason}")
        lines.append(f"- **is_tracked_in_backlog:** {item.is_tracked_in_backlog}")
        lines.append(f"- **is_untracked:** {item.is_untracked}")
        lines.append(f"- **is_external:** {item.is_external}")
        lines.append(f"- **backup_status:** {item.backup_status}")
        lines.append(f"- **approval_status:** {item.approval_status}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def write_json(items: list[FrozenCleanupInventoryItem], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([i.to_dict() for i in items], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(
    items: list[FrozenCleanupInventoryItem],
    out_path,
    release_hold: str,
) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    class_counts: dict[str, int] = {}
    for item in items:
        class_counts[item.cleanup_classification] = class_counts.get(item.cleanup_classification, 0) + 1
    manifest = {
        "total_items": len(items),
        "classification_counts": dict(sorted(class_counts.items())),
        "release_hold": release_hold,
        "simulation_only": True,
        "would_copy": False,
        "would_move": False,
        "would_delete": False,
        "would_modify": False,
        "no_touch_required": True,
        "human_approval_required": True,
        "inventory_hash": compute_inventory_hash(items),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(items: list[FrozenCleanupInventoryItem], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_inventory_markdown(items), encoding="utf-8")
