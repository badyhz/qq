"""Approval packet comparator."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class FieldDiff:
    field: str
    old_value: str
    new_value: str
    changed: bool
    def to_dict(self) -> dict:
        return {"field": self.field, "old_value": self.old_value, "new_value": self.new_value, "changed": self.changed}


@dataclass(frozen=True)
class ComparisonResult:
    comparison_id: str
    created_at: str
    packet_a_id: str
    packet_b_id: str
    diffs: tuple[FieldDiff, ...]
    checklist_diffs: tuple[dict, ...]
    identical: bool
    def to_dict(self) -> dict:
        return {"comparison_id": self.comparison_id, "created_at": self.created_at, "packet_a_id": self.packet_a_id, "packet_b_id": self.packet_b_id, "diffs": [d.to_dict() for d in self.diffs], "checklist_diffs": list(self.checklist_diffs), "identical": self.identical}


COMPARE_FIELDS = ("requested_scope", "allowed_scope", "prohibited_scope", "operator_ack", "human_approval_required", "submit_unlock_blocked", "decision")


def compare_packets(packet_a: dict, packet_b: dict) -> ComparisonResult:
    diffs: list[FieldDiff] = []
    for field in COMPARE_FIELDS:
        old = str(packet_a.get(field, ""))
        new = str(packet_b.get(field, ""))
        diffs.append(FieldDiff(field=field, old_value=old, new_value=new, changed=old != new))

    checklist_a = {c.get("item_id"): c for c in packet_a.get("checklists", [])}
    checklist_b = {c.get("item_id"): c for c in packet_b.get("checklists", [])}
    all_ids = sorted(set(list(checklist_a.keys()) + list(checklist_b.keys())))
    checklist_diffs: list[dict] = []
    for cid in all_ids:
        ca = checklist_a.get(cid, {})
        cb = checklist_b.get(cid, {})
        if ca != cb:
            checklist_diffs.append({"item_id": cid, "in_a": bool(ca), "in_b": bool(cb), "status_a": ca.get("status", ""), "status_b": cb.get("status", "")})

    identical = all(not d.changed for d in diffs) and len(checklist_diffs) == 0
    return ComparisonResult(
        comparison_id=f"CMP_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        packet_a_id=packet_a.get("packet_id", ""),
        packet_b_id=packet_b.get("packet_id", ""),
        diffs=tuple(diffs),
        checklist_diffs=tuple(checklist_diffs),
        identical=identical,
    )


def write_comparison(result: ComparisonResult, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def render_report(result: ComparisonResult) -> str:
    lines = ["# Approval Packet Comparator", "",
        f"**comparison_id={result.comparison_id}**",
        "**MOCK_COMPARISON_ONLY**",
        "**REAL_TESTNET_SUBMIT_NOT_ALLOWED**", "",
        f"Packet A: {result.packet_a_id}",
        f"Packet B: {result.packet_b_id}",
        f"Identical: {result.identical}", "",
        "## Field Diffs", "",
        "| Field | Old | New | Changed |",
        "|-------|-----|-----|---------|"]
    for d in result.diffs:
        lines.append(f"| {d.field} | {d.old_value} | {d.new_value} | {d.changed} |")
    if result.checklist_diffs:
        lines.extend(["", "## Checklist Diffs", ""])
        for cd in result.checklist_diffs:
            lines.append(f"- {cd['item_id']}: status_a={cd['status_a']}, status_b={cd['status_b']}")
    lines.extend(["", "## Conclusion", "", "APPROVAL_PACKET_COMPARATOR_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
