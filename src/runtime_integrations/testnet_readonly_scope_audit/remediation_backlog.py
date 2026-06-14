"""Remediation backlog."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class BacklogItem:
    task_id: str
    source_gap_id: str
    stage_id: str
    title: str
    priority: str  # P0, P1, P2, P3
    recommended_fix: str
    safe_to_auto_execute: bool
    requires_human_review: bool
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "source_gap_id": self.source_gap_id,
            "stage_id": self.stage_id, "title": self.title,
            "priority": self.priority, "recommended_fix": self.recommended_fix,
            "safe_to_auto_execute": self.safe_to_auto_execute,
            "requires_human_review": self.requires_human_review,
        }


@dataclass(frozen=True)
class RemediationBacklog:
    backlog_id: str
    created_at: str
    items: tuple[BacklogItem, ...]
    def to_dict(self) -> dict:
        return {"backlog_id": self.backlog_id, "created_at": self.created_at,
                "items": [i.to_dict() for i in self.items]}


BACKLOG_ITEMS = (
    BacklogItem("REM_001", "GAP_010", "STG_RO_002", "False positive fix already applied for safety regression", "P2", "Already remediated: environment variable and gate unlock references rewritten in SOP/evidence text", True, False),
    BacklogItem("REM_002", "GAP_019", "STG_RO_004", "Add more network-on blocker drill scenarios", "P2", "Expanded in T325001-T335000: 19 scenarios covering partial network, timeout, auth failure, rate limit, allowlist bypass, scope escalation, redaction bypass, kill switch bypass, rollback bypass", True, False),
    BacklogItem("REM_003", "GAP_023", "STG_RO_005", "Split dry execution integration tests into per-module files", "P3", "Test split completed in T325001-T335000: test_readonly_endpoint_allowlist_stub.py, test_readonly_audit_redaction_pack.py, test_readonly_dry_execution_artifact_manifest.py", True, False),
    BacklogItem("REM_004", "GAP_027", "STG_RO_006", "Split final governance integration tests into per-module files", "P3", "Test split completed in T325001-T335000: test_readonly_operator_handoff_packet.py, test_readonly_no_submit_release_archive.py, test_readonly_freeze_integrity_manifest.py", True, False),
    BacklogItem("REM_005", "GAP_032", "ALL", "Locate or create PRD source documents", "P3", "De facto spec registry created in T325001-T335000: all 6 stages documented with implementation as spec source", False, True),
    BacklogItem("REM_006", "ALL", "ALL", "No P0 safety boundary gaps found", "P0", "All safety boundaries verified: no real network, no real credentials, no submit unlock", True, False),
)


def create_backlog() -> RemediationBacklog:
    return RemediationBacklog(
        backlog_id=f"RBL_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        items=BACKLOG_ITEMS,
    )


def count_by_priority(backlog: RemediationBacklog) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in backlog.items:
        counts[item.priority] = counts.get(item.priority, 0) + 1
    return counts


def write_backlog(backlog: RemediationBacklog, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(backlog.to_dict(), indent=2), encoding="utf-8")


def render_report(backlog: RemediationBacklog) -> str:
    lines = ["# Remediation Backlog", "",
        f"**backlog_id={backlog.backlog_id}**",
        f"**total_items={len(backlog.items)}**", "",
        "## Priority Summary", ""]
    by_pri = count_by_priority(backlog)
    for pri, count in sorted(by_pri.items()):
        lines.append(f"- {pri}: {count}")
    lines.extend(["", "## Items", "",
        "| ID | Stage | Priority | Title | Auto-Safe |",
        "|----|-------|----------|-------|-----------|"])
    for item in backlog.items:
        lines.append(f"| {item.task_id} | {item.stage_id} | {item.priority} | {item.title} | {item.safe_to_auto_execute} |")
    lines.extend(["", "## Conclusion", "", "READONLY_REMEDIATION_BACKLOG_READY", ""])
    return "\n".join(lines)
