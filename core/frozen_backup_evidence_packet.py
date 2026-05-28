"""T16001 — Frozen Backup Evidence Packet renderer.

Pure deterministic. No I/O. No network.
Renders complete human-review packet from checklist + forms + validation + manifest + simulation.
No actual backup/archive/delete/move/copy operations.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

PACKET_SECTIONS: tuple[str, ...] = (
    "Executive Summary",
    "Safety Boundary",
    "Evidence Checklist Summary",
    "Manual Approval Form Summary",
    "Approval Validation Summary",
    "File-Level Evidence Requirements",
    "File-Level Approval Forms",
    "Required Hash Evidence",
    "Required Backup Evidence",
    "Required Rollback Evidence",
    "Pending Human Actions",
    "Forbidden Decisions",
    "Forbidden Automated Actions",
    "No Actual Backup Statement",
    "No Actual Archive/Delete Statement",
    "release_hold HOLD Statement",
    "Next Safe Actions",
)


@dataclass(frozen=True)
class EvidencePacket:
    """Complete evidence packet for human review."""
    sections: dict
    metadata: dict

    def to_dict(self) -> dict:
        return {
            "sections": self.sections,
            "metadata": self.metadata,
        }


def build_packet(
    checklist_items: list[dict],
    approval_forms: list[dict],
    validation_report: dict,
    backup_manifest: list[dict],
    archive_simulation: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> EvidencePacket:
    """Build complete evidence packet."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    sections: dict = {}

    # 1. Executive Summary
    sections["Executive Summary"] = {
        "total_checklist_items": len(checklist_items),
        "total_approval_forms": len(approval_forms),
        "total_manifest_items": len(backup_manifest),
        "total_simulation_items": len(archive_simulation),
        "validation_all_passed": validation_report.get("all_passed", False),
        "validation_total_checks": validation_report.get("total_checks", 0),
        "validation_passed_checks": validation_report.get("passed_checks", 0),
        "release_hold": release_hold,
        "advisory_only": True,
        "human_review_required": True,
    }

    # 2. Safety Boundary
    sections["Safety Boundary"] = {
        "no_actual_backup": True,
        "no_actual_archive": True,
        "no_actual_delete": True,
        "no_actual_move": True,
        "no_actual_copy": True,
        "no_actual_execution": True,
        "no_actual_import": True,
        "no_live_activation": True,
        "no_testnet_activation": True,
        "no_runtime_activation": True,
        "release_hold": release_hold,
        "advisory_only": True,
    }

    # 3. Evidence Checklist Summary
    blocker_counts: dict[str, int] = {}
    evidence_status_counts: dict[str, int] = {}
    for item in checklist_items:
        bs = item.get("blocker_status", "UNKNOWN")
        blocker_counts[bs] = blocker_counts.get(bs, 0) + 1
        es = item.get("evidence_status", "UNKNOWN")
        evidence_status_counts[es] = evidence_status_counts.get(es, 0) + 1

    sections["Evidence Checklist Summary"] = {
        "total_items": len(checklist_items),
        "blocker_counts": blocker_counts,
        "evidence_status_counts": evidence_status_counts,
        "all_pending": all(item.get("evidence_status") == "PENDING" for item in checklist_items),
        "none_complete": all(item.get("evidence_status") != "COMPLETE" for item in checklist_items),
    }

    # 4. Manual Approval Form Summary
    form_type_counts: dict[str, int] = {}
    for form in approval_forms:
        ft = form.get("form_type", "UNKNOWN")
        form_type_counts[ft] = form_type_counts.get(ft, 0) + 1

    sections["Manual Approval Form Summary"] = {
        "total_forms": len(approval_forms),
        "form_type_counts": form_type_counts,
        "all_decisions_placeholders": all(
            f.get("human_decision_placeholder") == "PENDING_HUMAN_DECISION"
            for f in approval_forms
        ),
    }

    # 5. Approval Validation Summary
    sections["Approval Validation Summary"] = {
        "total_checks": validation_report.get("total_checks", 0),
        "passed_checks": validation_report.get("passed_checks", 0),
        "failed_checks": validation_report.get("failed_checks", 0),
        "all_passed": validation_report.get("all_passed", False),
    }

    # 6. File-Level Evidence Requirements
    file_evidence = {}
    for item in checklist_items:
        file_evidence[item["path"]] = {
            "required_evidence": item.get("required_evidence", []),
            "required_hash_evidence": item.get("required_hash_evidence", []),
            "required_size_evidence": item.get("required_size_evidence", []),
            "required_path_evidence": item.get("required_path_evidence", []),
            "evidence_status": item.get("evidence_status", "PENDING"),
            "blocker_status": item.get("blocker_status", "UNKNOWN"),
        }
    sections["File-Level Evidence Requirements"] = file_evidence

    # 7. File-Level Approval Forms
    file_forms = {}
    for form in approval_forms:
        file_forms[form["path"]] = {
            "form_id": form.get("form_id"),
            "form_type": form.get("form_type"),
            "candidate_action": form.get("candidate_action"),
            "human_decision_placeholder": form.get("human_decision_placeholder"),
            "approval_conditions": form.get("approval_conditions", []),
        }
    sections["File-Level Approval Forms"] = file_forms

    # 8. Required Hash Evidence
    hash_evidence = {}
    for item in checklist_items:
        hash_evidence[item["path"]] = {
            "sha256": _extract_from_evidence(item.get("required_hash_evidence", []), "known_hash="),
            "hash_evidence_items": item.get("required_hash_evidence", []),
        }
    sections["Required Hash Evidence"] = hash_evidence

    # 9. Required Backup Evidence
    backup_evidence = {}
    for item in backup_manifest:
        backup_evidence[item.get("path", "")] = {
            "backup_class": item.get("backup_class"),
            "backup_required": item.get("backup_required"),
            "backup_allowed_now": item.get("backup_allowed_now"),
            "proposed_backup_path": item.get("proposed_backup_path"),
            "required_backup_evidence": item.get("required_backup_evidence", []),
        }
    sections["Required Backup Evidence"] = backup_evidence

    # 10. Required Rollback Evidence
    rollback_evidence = {}
    for item in checklist_items:
        rollback_evidence[item["path"]] = {
            "required_rollback_note": item.get("required_rollback_note", ""),
            "rollback_plan_reviewed": "rollback_plan_reviewed" in item.get("required_evidence", []),
        }
    sections["Required Rollback Evidence"] = rollback_evidence

    # 11. Pending Human Actions
    pending_actions = []
    for item in checklist_items:
        pending_actions.append({
            "path": item["path"],
            "action": "collect_evidence",
            "blocker_status": item.get("blocker_status"),
            "evidence_status": item.get("evidence_status"),
        })
    for form in approval_forms:
        pending_actions.append({
            "path": form["path"],
            "action": "complete_approval_form",
            "form_type": form.get("form_type"),
            "human_decision": form.get("human_decision_placeholder"),
        })
    sections["Pending Human Actions"] = pending_actions

    # 12. Forbidden Decisions
    from core.frozen_approval_validator import FORBIDDEN_DECISIONS
    sections["Forbidden Decisions"] = list(FORBIDDEN_DECISIONS)

    # 13. Forbidden Automated Actions
    sections["Forbidden Automated Actions"] = [
        "automated_backup",
        "automated_archive",
        "automated_delete",
        "automated_move",
        "automated_copy",
        "automated_execution",
        "automated_import",
        "automated_live_activation",
        "automated_testnet_activation",
        "automated_runtime_activation",
    ]

    # 14. No Actual Backup Statement
    sections["No Actual Backup Statement"] = {
        "statement": "No actual backup has been performed. This packet is evidence preparation only.",
        "no_backup_performed": True,
    }

    # 15. No Actual Archive/Delete Statement
    sections["No Actual Archive/Delete Statement"] = {
        "statement": "No actual archive, delete, move, or copy has been performed. This packet is evidence preparation only.",
        "no_archive_performed": True,
        "no_delete_performed": True,
        "no_move_performed": True,
        "no_copy_performed": True,
    }

    # 16. release_hold HOLD Statement
    sections["release_hold HOLD Statement"] = {
        "statement": "release_hold remains HOLD. No action may be taken until explicitly released by human authority.",
        "release_hold": release_hold,
        "cannot_be_overridden_by_automation": True,
    }

    # 17. Next Safe Actions
    sections["Next Safe Actions"] = {
        "recommended_next_phase": "T16501-T17000 Offline Backup Approval Dry-Run Validator / Completed Form Simulation",
        "still_no_actual_backup": True,
        "still_no_actual_copy_move_delete": True,
        "steps": [
            "1. Human reviews evidence checklist",
            "2. Human collects hash evidence for each file",
            "3. Human collects size evidence for each file",
            "4. Human confirms paths",
            "5. Human assigns owners",
            "6. Human reviews rollback plans",
            "7. Human completes approval forms",
            "8. Validator checks completed forms",
            "9. Only then consider next phase",
        ],
    }

    metadata = {
        "release_hold": release_hold,
        "advisory_only": True,
        "human_review_required": True,
        "total_sections": len(sections),
        "sections_present": list(sections.keys()),
        "packet_hash": hashlib.sha256(
            json.dumps(sections, sort_keys=True, indent=2).encode()
        ).hexdigest(),
    }

    return EvidencePacket(sections=sections, metadata=metadata)


def _extract_from_evidence(evidence_list: list[str], prefix: str) -> str:
    for ev in evidence_list:
        if ev.startswith(prefix):
            return ev[len(prefix):]
    return ""


def render_packet_markdown(packet: EvidencePacket) -> str:
    lines = [
        "# Frozen File Backup Evidence Packet",
        "",
        f"**Total sections:** {packet.metadata['total_sections']}",
        f"**release_hold:** {packet.metadata['release_hold']}",
        f"**advisory_only:** {packet.metadata['advisory_only']}",
        f"**human_review_required:** {packet.metadata['human_review_required']}",
        "",
    ]

    for section_name in PACKET_SECTIONS:
        section_data = packet.sections.get(section_name)
        if section_data is None:
            continue
        lines.append(f"## {section_name}")
        lines.append("")
        if isinstance(section_data, dict):
            for k, v in section_data.items():
                if isinstance(v, list):
                    lines.append(f"**{k}:**")
                    for item in v:
                        if isinstance(item, dict):
                            lines.append(f"  - {json.dumps(item)}")
                        else:
                            lines.append(f"  - {item}")
                else:
                    lines.append(f"- **{k}:** {v}")
        elif isinstance(section_data, list):
            for item in section_data:
                if isinstance(item, dict):
                    lines.append(f"- {json.dumps(item)}")
                else:
                    lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def render_packet_html(packet: EvidencePacket) -> str:
    """Render standalone offline HTML. No CDN, no external JS, no web server."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "<title>Frozen File Backup Evidence Packet</title>",
        "<style>",
        "body { font-family: monospace; max-width: 1200px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #e0e0e0; }",
        "h1 { color: #ff6b6b; border-bottom: 2px solid #ff6b6b; }",
        "h2 { color: #4ecdc4; margin-top: 30px; }",
        ".safety { background: #2d1b1b; border: 2px solid #ff6b6b; padding: 15px; margin: 15px 0; }",
        ".pending { background: #1b2d1b; border: 1px solid #4ecdc4; padding: 10px; margin: 10px 0; }",
        ".forbidden { background: #2d1b1b; border: 1px solid #ff6b6b; padding: 10px; margin: 10px 0; }",
        "table { border-collapse: collapse; width: 100%; margin: 10px 0; }",
        "th, td { border: 1px solid #444; padding: 8px; text-align: left; }",
        "th { background: #2a2a4a; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Frozen File Backup Evidence Packet</h1>",
        f"<p><strong>release_hold:</strong> {packet.metadata['release_hold']}</p>",
        f"<p><strong>advisory_only:</strong> {packet.metadata['advisory_only']}</p>",
        f"<p><strong>human_review_required:</strong> {packet.metadata['human_review_required']}</p>",
    ]

    for section_name in PACKET_SECTIONS:
        section_data = packet.sections.get(section_name)
        if section_data is None:
            continue
        html_parts.append(f"<h2>{section_name}</h2>")

        if section_name in ("Safety Boundary", "No Actual Backup Statement", "No Actual Archive/Delete Statement", "release_hold HOLD Statement"):
            html_parts.append("<div class='safety'>")
        elif section_name in ("Forbidden Decisions", "Forbidden Automated Actions"):
            html_parts.append("<div class='forbidden'>")
        else:
            html_parts.append("<div class='pending'>")

        if isinstance(section_data, dict):
            html_parts.append("<table>")
            for k, v in section_data.items():
                if isinstance(v, list):
                    html_parts.append(f"<tr><th>{k}</th><td><ul>")
                    for item in v:
                        if isinstance(item, dict):
                            html_parts.append(f"<li><code>{json.dumps(item)}</code></li>")
                        else:
                            html_parts.append(f"<li>{item}</li>")
                    html_parts.append("</ul></td></tr>")
                else:
                    html_parts.append(f"<tr><th>{k}</th><td>{v}</td></tr>")
            html_parts.append("</table>")
        elif isinstance(section_data, list):
            html_parts.append("<ul>")
            for item in section_data:
                if isinstance(item, dict):
                    html_parts.append(f"<li><code>{json.dumps(item)}</code></li>")
                else:
                    html_parts.append(f"<li>{item}</li>")
            html_parts.append("</ul>")

        html_parts.append("</div>")

    html_parts.extend([
        "</body>",
        "</html>",
    ])

    return "\n".join(html_parts)


def write_json(packet: EvidencePacket, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")


def write_manifest(packet: EvidencePacket, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(packet.metadata, indent=2), encoding="utf-8")


def write_markdown(packet: EvidencePacket, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_packet_markdown(packet), encoding="utf-8")


def write_html(packet: EvidencePacket, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_packet_html(packet), encoding="utf-8")
