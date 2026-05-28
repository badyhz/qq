"""Research review blocker resolution ledger.

Program E: Blocker Resolution Ledger.
Generates and validates blocker_resolution_ledger.json and .md.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

BLOCKER_LEDGER_VERSION = "1.0.0"

ALLOWED_BLOCKER_STATUSES = (
    "OPEN",
    "RESOLVED_ADVISORY_ONLY",
    "ACCEPTED_RISK_ADVISORY_ONLY",
    "REJECTED",
)

FORBIDDEN_BLOCKER_STATUSES = (
    "RESOLVED_FOR_LIVE",
    "RESOLVED_FOR_TESTNET",
    "AUTO_CLEARED",
)


def build_blocker_ledger(
    blockers: List[Dict[str, Any]],
    generated_at: str = "deterministic",
) -> Dict[str, Any]:
    """Build blocker resolution ledger."""
    entries = []
    for b in blockers:
        entry = {
            "blocker_id": b.get("blocker_id", "UNKNOWN"),
            "source": b.get("source", "unknown"),
            "severity": b.get("severity", "UNKNOWN"),
            "status": "OPEN",
            "resolution_note": "",
            "evidence_path": b.get("evidence_path", ""),
            "resolved_by": "",
            "resolved_at": "",
        }
        entries.append(entry)

    return {
        "schema_version": "1.0.0",
        "ledger_version": BLOCKER_LEDGER_VERSION,
        "generated_at": generated_at,
        "total_blockers": len(entries),
        "open_blockers": sum(1 for e in entries if e["status"] == "OPEN"),
        "entries": entries,
    }


def validate_blocker_ledger(ledger: Dict[str, Any]) -> Tuple[bool, Tuple[str, ...]]:
    """Validate blocker resolution ledger."""
    errors: List[str] = []

    entries = ledger.get("entries", [])
    for entry in entries:
        status = entry.get("status", "")
        bid = entry.get("blocker_id", "UNKNOWN")

        if status not in ALLOWED_BLOCKER_STATUSES:
            errors.append(f"blocker {bid}: status {status!r} not in allowed statuses")

        if status in FORBIDDEN_BLOCKER_STATUSES:
            errors.append(f"blocker {bid}: status {status!r} is explicitly forbidden")

        # Resolved entries need resolution info
        if status in ("RESOLVED_ADVISORY_ONLY", "ACCEPTED_RISK_ADVISORY_ONLY"):
            if not entry.get("resolved_by", "").strip():
                errors.append(f"blocker {bid}: resolved but missing resolved_by")
            if not entry.get("resolution_note", "").strip():
                errors.append(f"blocker {bid}: resolved but missing resolution_note")

    return (len(errors) == 0, tuple(errors))


def render_blocker_ledger_markdown(ledger: Dict[str, Any]) -> str:
    """Render blocker ledger as markdown."""
    lines: List[str] = []
    lines.append("# Blocker Resolution Ledger")
    lines.append("")
    lines.append(f"Version: {ledger.get('ledger_version', 'unknown')}")
    lines.append(f"Generated: {ledger.get('generated_at', 'unknown')}")
    lines.append(f"Total blockers: {ledger.get('total_blockers', 0)}")
    lines.append(f"Open blockers: {ledger.get('open_blockers', 0)}")
    lines.append("")
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("Allowed statuses: OPEN, RESOLVED_ADVISORY_ONLY, ACCEPTED_RISK_ADVISORY_ONLY, REJECTED")
    lines.append("")
    lines.append("Forbidden statuses: RESOLVED_FOR_LIVE, RESOLVED_FOR_TESTNET, AUTO_CLEARED")
    lines.append("")
    lines.append("## Entries")
    lines.append("")

    for entry in ledger.get("entries", []):
        lines.append(f"### {entry.get('blocker_id', 'UNKNOWN')}")
        lines.append("")
        lines.append(f"- Source: {entry.get('source', '')}")
        lines.append(f"- Severity: {entry.get('severity', '')}")
        lines.append(f"- Status: {entry.get('status', '')}")
        if entry.get("resolution_note"):
            lines.append(f"- Resolution: {entry.get('resolution_note', '')}")
        if entry.get("resolved_by"):
            lines.append(f"- Resolved by: {entry.get('resolved_by', '')}")
        if entry.get("evidence_path"):
            lines.append(f"- Evidence: {entry.get('evidence_path', '')}")
        lines.append("")

    return "\n".join(lines)
