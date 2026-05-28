"""T16501 — Frozen Completed Form Report.

Pure deterministic. No I/O. No network.
Renders comprehensive report from simulation, validation, and matrix data.
No actual approval granted. No actual action performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"


def render_report_json(
    simulations: dict,
    validation: dict,
    matrix: dict,
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> dict:
    """Render full report as JSON dict."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    sim_count = simulations.get("total_count", 0)
    val = validation
    val_total = val.get("total_count", 0)
    val_accepted = val.get("accepted_count", 0)
    val_rejected = val.get("rejected_count", 0)
    val_needs = val.get("needs_review_count", 0)
    mat = matrix
    mat_entries = mat.get("entries", [])

    # Extract forbidden decision rejections
    forbidden_rejections = [
        r for r in val.get("results", [])
        if r.get("outcome") == "DRY_RUN_REJECTED_FORBIDDEN_DECISION"
    ]
    missing_evidence_rejections = [
        r for r in val.get("results", [])
        if r.get("outcome") == "DRY_RUN_REJECTED_MISSING_EVIDENCE"
    ]
    release_hold_overrides = [
        r for r in val.get("results", [])
        if r.get("outcome") == "DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE"
    ]
    unsafe_actions = [
        r for r in val.get("results", [])
        if r.get("outcome") == "DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST"
    ]
    accepted = [
        r for r in val.get("results", [])
        if r.get("outcome") == "DRY_RUN_ACCEPTED_PREPARE_ONLY"
    ]
    needs_review = [
        r for r in val.get("results", [])
        if r.get("outcome") == "DRY_RUN_NEEDS_MORE_REVIEW"
    ]

    return {
        "report_type": "frozen_completed_form_report",
        "release_hold": release_hold,
        "action_authorized": False,
        "no_action_performed": True,
        "sections": {
            "executive_summary": {
                "title": "Executive Summary",
                "total_simulations": sim_count,
                "total_validated": val_total,
                "accepted_prepare_only": val_accepted,
                "rejected": val_rejected,
                "needs_more_review": val_needs,
                "action_authorized": False,
                "no_action_performed": True,
            },
            "safety_boundary": {
                "title": "Safety Boundary",
                "release_hold": release_hold,
                "advisory_only": True,
                "human_review_required": True,
                "no_action_authorized": True,
                "no_backup_performed": True,
                "no_archive_performed": True,
                "no_delete_performed": True,
                "no_move_performed": True,
                "no_copy_performed": True,
                "no_activation_performed": True,
            },
            "simulation_scope": {
                "title": "Simulation Scope",
                "total_simulations": sim_count,
                "category_counts": simulations.get("category_counts", {}),
                "dry_run_only": True,
            },
            "completed_form_categories": {
                "title": "Completed Form Categories",
                "categories": sorted(simulations.get("category_counts", {}).keys()),
            },
            "accepted_prepare_only": {
                "title": "Accepted Prepare-Only Outcomes",
                "count": len(accepted),
                "forms": [
                    {"form_id": r["completed_form_id"], "path": r["path"], "decision_reason": r["reason"]}
                    for r in accepted[:10]
                ],
                "note": "Accepted prepare-only means the form passed validation but NO ACTION is authorized.",
            },
            "rejected_forbidden_decisions": {
                "title": "Rejected Forbidden Decisions",
                "count": len(forbidden_rejections),
                "forms": [
                    {"form_id": r["completed_form_id"], "path": r["path"], "reason": r["reason"]}
                    for r in forbidden_rejections
                ],
            },
            "rejected_missing_evidence": {
                "title": "Rejected Missing Evidence",
                "count": len(missing_evidence_rejections),
                "forms": [
                    {"form_id": r["completed_form_id"], "path": r["path"], "reason": r["reason"]}
                    for r in missing_evidence_rejections
                ],
            },
            "release_hold_override_attempts": {
                "title": "Release Hold Override Attempts",
                "count": len(release_hold_overrides),
                "forms": [
                    {"form_id": r["completed_form_id"], "path": r["path"], "reason": r["reason"]}
                    for r in release_hold_overrides
                ],
                "release_hold": release_hold,
            },
            "unsafe_auto_action_requests": {
                "title": "Unsafe Auto Action Requests",
                "count": len(unsafe_actions),
                "forms": [
                    {"form_id": r["completed_form_id"], "path": r["path"], "reason": r["reason"]}
                    for r in unsafe_actions
                ],
            },
            "outcome_matrix": {
                "title": "Outcome Matrix",
                "total_outcomes": mat.get("total_outcomes", 0),
                "entries": mat_entries,
            },
            "pending_human_review": {
                "title": "Pending Human Review",
                "count": len(needs_review),
                "forms": [
                    {"form_id": r["completed_form_id"], "path": r["path"]}
                    for r in needs_review
                ],
            },
            "no_action_authorized_statement": {
                "title": "No Action Authorized Statement",
                "statement": "NO ACTION IS AUTHORIZED BY THIS REPORT. All outcomes are dry-run validation results only. No backup, archive, delete, move, copy, rename, activation, or execution is performed or authorized.",
            },
            "no_file_operation_statement": {
                "title": "No File Operation Statement",
                "statement": "No file operations are performed. No files are created, deleted, moved, copied, renamed, or archived by this report or its validation pipeline.",
            },
            "forbidden_actions": {
                "title": "Forbidden Actions",
                "actions": [
                    "DELETE_NOW", "MOVE_NOW", "COPY_NOW", "ARCHIVE_NOW",
                    "EXECUTE_NOW", "IMPORT_NOW", "ACTIVATE_LIVE", "ACTIVATE_TESTNET",
                    "ENABLE_RUNTIME", "ENABLE_PLANNER", "SUBMIT_ORDER", "CANCEL_ORDER",
                    "FLATTEN_POSITION",
                ],
            },
            "release_hold_statement": {
                "title": "release_hold HOLD Statement",
                "release_hold": release_hold,
                "statement": "release_hold remains HOLD. No action can be taken until a human explicitly changes this value through a separate governance process.",
            },
            "next_safe_actions": {
                "title": "Next Safe Actions",
                "recommended_phase": "T17001-T17500 Offline Frozen File Cleanup Governance Finalization",
                "actions": [
                    "Review completed form simulations for accuracy",
                    "Review dry-run validation outcomes",
                    "Review outcome matrix for decision patterns",
                    "No actual cleanup, archive, delete, move, or copy",
                    "Still no activation of live/testnet/runtime",
                ],
            },
        },
    }


def render_report_markdown(report: dict) -> str:
    """Render report as markdown."""
    sections = report.get("sections", {})
    lines = [
        "# Frozen Completed Form Report",
        "",
        f"**release_hold:** {report.get('release_hold', 'UNKNOWN')}",
        f"**action_authorized:** {report.get('action_authorized', False)}",
        f"**no_action_performed:** {report.get('no_action_performed', True)}",
        "",
    ]
    for key, section in sections.items():
        title = section.get("title", key)
        lines.append(f"## {title}")
        lines.append("")
        if "statement" in section:
            lines.append(section["statement"])
        elif "note" in section:
            lines.append(section["note"])
        # Render counts
        for field in ("count", "total_simulations", "total_validated", "total_outcomes",
                       "accepted_prepare_only", "rejected", "needs_more_review"):
            if field in section:
                lines.append(f"- **{field}:** {section[field]}")
        # Render forms
        if "forms" in section:
            for f in section["forms"][:5]:
                fid = f.get("form_id", "")
                path = f.get("path", "")
                reason = f.get("reason", f.get("decision_reason", ""))
                lines.append(f"  - {fid} ({path}): {reason}")
            if len(section.get("forms", [])) > 5:
                lines.append(f"  - ... and {len(section['forms']) - 5} more")
        # Render entries
        if "entries" in section:
            for e in section["entries"][:5]:
                lines.append(f"  - {e.get('outcome', '')}: {e.get('count', 0)} forms")
        # Render actions
        if "actions" in section and isinstance(section["actions"], list) and section["actions"] and isinstance(section["actions"][0], str):
            for a in section["actions"]:
                lines.append(f"- {a}")
        # Render categories
        if "categories" in section:
            for c in section["categories"]:
                lines.append(f"- {c}")
        lines.append("")

    lines.append("---")
    lines.append("NO ACTION AUTHORIZED. DRY-RUN REPORT ONLY.")
    lines.append("")
    return "\n".join(lines)


def render_report_html(report: dict) -> str:
    """Render report as standalone offline HTML."""
    sections = report.get("sections", {})
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "<title>Frozen Completed Form Report</title>",
        "<style>",
        "body { font-family: monospace; max-width: 1200px; margin: 0 auto; padding: 20px; background: #1a1a1a; color: #e0e0e0; }",
        "h1 { color: #ff6b6b; border-bottom: 2px solid #ff6b6b; padding-bottom: 10px; }",
        "h2 { color: #4ecdc4; margin-top: 30px; }",
        "table { border-collapse: collapse; width: 100%; margin: 10px 0; }",
        "th, td { border: 1px solid #444; padding: 8px; text-align: left; }",
        "th { background: #333; color: #4ecdc4; }",
        ".warning { background: #4a1a1a; border: 2px solid #ff6b6b; padding: 15px; margin: 10px 0; }",
        ".accepted { color: #4ecdc4; }",
        ".rejected { color: #ff6b6b; }",
        ".needs-review { color: #ffd93d; }",
        "ul { padding-left: 20px; }",
        "li { margin: 5px 0; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Frozen Completed Form Report</h1>",
        f"<p><strong>release_hold:</strong> {report.get('release_hold', 'UNKNOWN')}</p>",
        f"<p><strong>action_authorized:</strong> {report.get('action_authorized', False)}</p>",
        f"<p><strong>no_action_performed:</strong> {report.get('no_action_performed', True)}</p>",
    ]

    for key, section in sections.items():
        title = section.get("title", key)
        html_parts.append(f"<h2>{title}</h2>")
        if "statement" in section:
            html_parts.append(f"<div class='warning'><p>{section['statement']}</p></div>")
        if "note" in section:
            html_parts.append(f"<p><em>{section['note']}</em></p>")
        for field in ("count", "total_simulations", "total_validated", "total_outcomes",
                       "accepted_prepare_only", "rejected", "needs_more_review"):
            if field in section:
                html_parts.append(f"<p><strong>{field}:</strong> {section[field]}</p>")
        if "forms" in section and section["forms"]:
            html_parts.append("<table><tr><th>Form ID</th><th>Path</th><th>Reason</th></tr>")
            for f in section["forms"][:10]:
                html_parts.append(f"<tr><td>{f.get('form_id','')}</td><td>{f.get('path','')}</td><td>{f.get('reason', f.get('decision_reason',''))}</td></tr>")
            html_parts.append("</table>")
        if "entries" in section and section["entries"]:
            html_parts.append("<table><tr><th>Outcome</th><th>Count</th><th>Action Authorized</th></tr>")
            for e in section["entries"]:
                html_parts.append(f"<tr><td>{e.get('outcome','')}</td><td>{e.get('count',0)}</td><td>false</td></tr>")
            html_parts.append("</table>")
        if "actions" in section and isinstance(section.get("actions"), list) and section["actions"] and isinstance(section["actions"][0], str):
            html_parts.append("<ul>")
            for a in section["actions"]:
                html_parts.append(f"<li>{a}</li>")
            html_parts.append("</ul>")
        if "categories" in section:
            html_parts.append("<ul>")
            for c in section["categories"]:
                html_parts.append(f"<li>{c}</li>")
            html_parts.append("</ul>")

    html_parts.append("<hr>")
    html_parts.append("<div class='warning'><p>NO ACTION AUTHORIZED. DRY-RUN REPORT ONLY.</p></div>")
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def render_manifest(report: dict) -> dict:
    h = hashlib.sha256(
        json.dumps(report, sort_keys=True, indent=2).encode()
    ).hexdigest()
    return {
        "report_type": "frozen_completed_form_report",
        "release_hold": report.get("release_hold"),
        "action_authorized": False,
        "total_sections": len(report.get("sections", {})),
        "report_hash": h,
    }
