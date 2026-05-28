"""T15001 — Frozen File Disposition Report renderer.

Pure deterministic. No I/O. No network. No execution.
Reads queue + decision prep, produces human-friendly report.
"""
from __future__ import annotations

import html as html_mod
import json
import pathlib
from collections import Counter

RELEASE_HOLD_REQUIRED = "HOLD"


def _load_json(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}\n"


def build_report(
    queue_items: list[dict],
    prep_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> dict:
    """Build disposition report structure."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    priority_counts = Counter(q["priority"] for q in queue_items)
    disposition_counts = Counter(q["disposition"] for q in queue_items)
    candidate_counts = Counter(p["candidate_action"] for p in prep_items)

    p0_items = [q for q in queue_items if q["priority"] == "P0_CRITICAL_REVIEW"]
    p1_items = [q for q in queue_items if q["priority"] == "P1_HIGH_REVIEW"]
    archive_candidates = [p for p in prep_items if p["candidate_action"] == "PREPARE_ARCHIVE_AFTER_BACKUP"]
    delete_candidates = [p for p in prep_items if p["candidate_action"] == "PREPARE_DELETE_AFTER_BACKUP"]
    rewrite_candidates = [p for p in prep_items if p["candidate_action"] == "PREPARE_OFFLINE_REWRITE"]
    keep_frozen_items = [p for p in prep_items if p["candidate_action"] == "KEEP_FROZEN"]
    unknown_items = [q for q in queue_items if q["priority"] == "UNKNOWN_REVIEW"]

    return {
        "executive_summary": {
            "total_frozen_files": len(queue_items),
            "release_hold": release_hold,
            "advisory_only": True,
            "human_review_required": True,
            "no_touch_required": True,
        },
        "safety_boundary": {
            "deletion_allowed_now": False,
            "archive_allowed_now": False,
            "rewrite_allowed_now": False,
            "required_human_approval": True,
            "no_touch_until_approved": True,
        },
        "frozen_file_count": len(queue_items),
        "priority_breakdown": dict(priority_counts),
        "disposition_breakdown": dict(disposition_counts),
        "candidate_action_breakdown": dict(candidate_counts),
        "p0_critical_review_items": [_item_summary(q) for q in p0_items],
        "p1_high_review_items": [_item_summary(q) for q in p1_items],
        "archive_candidates": [_prep_summary(p) for p in archive_candidates],
        "delete_after_backup_candidates": [_prep_summary(p) for p in delete_candidates],
        "offline_rewrite_candidates": [_prep_summary(p) for p in rewrite_candidates],
        "keep_frozen_items": [_prep_summary(p) for p in keep_frozen_items],
        "unknown_items": [_item_summary(q) for q in unknown_items],
        "required_human_decisions": [
            {"path": q["path"], "decision_placeholder": "AWAITING_HUMAN_DECISION"}
            for q in queue_items
        ],
        "required_backup_evidence": [
            {"path": p["path"], "evidence": p["required_backup_evidence"]}
            for p in prep_items if p["backup_required"]
        ],
        "forbidden_actions": [
            "EXECUTE", "IMPORT", "ACTIVATE_LIVE", "ACTIVATE_TESTNET",
            "ENABLE_RUNTIME", "ENABLE_PLANNER", "SUBMIT_ORDER",
            "CANCEL_ORDER", "FLATTEN_POSITION", "APPROVE_WITHOUT_BACKUP",
            "DELETE_NOW", "MOVE_NOW", "EXECUTE_NOW", "IMPORT_NOW", "ACTIVATE_NOW",
        ],
        "no_touch_statement": (
            "All frozen files require explicit human review and approval before any action. "
            "No file may be executed, imported, staged, moved, deleted, or renamed without approval. "
            "release_hold is HOLD. advisory_only is true. human_review_required is true."
        ),
        "release_hold_statement": "release_hold = HOLD. No activation permitted.",
        "next_safe_actions": [
            "Review P0 critical items first",
            "Verify backup evidence for all archive/delete candidates",
            "Record human decisions in final_manual_decision_placeholder",
            "Proceed to T15501-T16000: Offline Backup Manifest / Archive Simulation",
        ],
    }


def _item_summary(q: dict) -> dict:
    return {
        "queue_id": q.get("queue_id", ""),
        "path": q["path"],
        "priority": q["priority"],
        "disposition": q.get("disposition", ""),
        "category": q.get("category", ""),
        "risk_score": q.get("risk_score", 0),
    }


def _prep_summary(p: dict) -> dict:
    return {
        "path": p["path"],
        "priority": p["priority"],
        "candidate_action": p["candidate_action"],
        "backup_required": p["backup_required"],
        "rollback_plan": p["rollback_plan"],
    }


def render_markdown(report: dict) -> str:
    """Render disposition report as markdown."""
    lines = [
        "# Frozen File Disposition Report",
        "",
    ]

    # Executive Summary
    es = report["executive_summary"]
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(f"- **Total frozen files:** {es['total_frozen_files']}")
    lines.append(f"- **release_hold:** {es['release_hold']}")
    lines.append(f"- **advisory_only:** {es['advisory_only']}")
    lines.append(f"- **human_review_required:** {es['human_review_required']}")
    lines.append("")

    # Safety Boundary
    sb = report["safety_boundary"]
    lines.append("## 2. Safety Boundary")
    lines.append("")
    for k, v in sb.items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")

    # Frozen File Count
    lines.append("## 3. Frozen File Count")
    lines.append("")
    lines.append(f"Total: **{report['frozen_file_count']}**")
    lines.append("")

    # Priority Breakdown
    lines.append("## 4. Priority Breakdown")
    lines.append("")
    for k, v in report["priority_breakdown"].items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")

    # Disposition Breakdown
    lines.append("## 5. Disposition Breakdown")
    lines.append("")
    for k, v in report["disposition_breakdown"].items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")

    # P0 Critical Review Items
    lines.append("## 6. P0 Critical Review Items")
    lines.append("")
    for item in report["p0_critical_review_items"]:
        lines.append(f"- **{item['path']}** (category={item['category']}, risk={item['risk_score']}, disposition={item['disposition']})")
    if not report["p0_critical_review_items"]:
        lines.append("None.")
    lines.append("")

    # P1 High Review Items
    lines.append("## 7. P1 High Review Items")
    lines.append("")
    for item in report["p1_high_review_items"]:
        lines.append(f"- **{item['path']}** (category={item['category']}, risk={item['risk_score']}, disposition={item['disposition']})")
    if not report["p1_high_review_items"]:
        lines.append("None.")
    lines.append("")

    # Archive Candidates
    lines.append("## 8. Archive Candidates")
    lines.append("")
    for item in report["archive_candidates"]:
        lines.append(f"- **{item['path']}** — backup_required={item['backup_required']}")
    if not report["archive_candidates"]:
        lines.append("None.")
    lines.append("")

    # Delete After Backup Candidates
    lines.append("## 9. Delete After Backup Candidates")
    lines.append("")
    for item in report["delete_after_backup_candidates"]:
        lines.append(f"- **{item['path']}** — backup_required={item['backup_required']}")
    if not report["delete_after_backup_candidates"]:
        lines.append("None.")
    lines.append("")

    # Offline Rewrite Candidates
    lines.append("## 10. Offline Rewrite Candidates")
    lines.append("")
    for item in report["offline_rewrite_candidates"]:
        lines.append(f"- **{item['path']}** — backup_required={item['backup_required']}")
    if not report["offline_rewrite_candidates"]:
        lines.append("None.")
    lines.append("")

    # Keep Frozen Items
    lines.append("## 11. Keep Frozen Items")
    lines.append("")
    for item in report["keep_frozen_items"]:
        lines.append(f"- **{item['path']}**")
    if not report["keep_frozen_items"]:
        lines.append("None.")
    lines.append("")

    # Unknown Items
    lines.append("## 12. Unknown Items")
    lines.append("")
    for item in report["unknown_items"]:
        lines.append(f"- **{item['path']}** (risk={item['risk_score']})")
    if not report["unknown_items"]:
        lines.append("None.")
    lines.append("")

    # Required Human Decisions
    lines.append("## 13. Required Human Decisions")
    lines.append("")
    for item in report["required_human_decisions"]:
        lines.append(f"- **{item['path']}** — {item['decision_placeholder']}")
    lines.append("")

    # Required Backup Evidence
    lines.append("## 14. Required Backup Evidence")
    lines.append("")
    for item in report["required_backup_evidence"]:
        lines.append(f"- **{item['path']}:** {', '.join(item['evidence'])}")
    if not report["required_backup_evidence"]:
        lines.append("None.")
    lines.append("")

    # Forbidden Actions
    lines.append("## 15. Forbidden Actions")
    lines.append("")
    for action in report["forbidden_actions"]:
        lines.append(f"- {action}")
    lines.append("")

    # No-Touch Statement
    lines.append("## 16. No-Touch Statement")
    lines.append("")
    lines.append(report["no_touch_statement"])
    lines.append("")

    # release_hold HOLD Statement
    lines.append("## 17. release_hold HOLD Statement")
    lines.append("")
    lines.append(report["release_hold_statement"])
    lines.append("")

    # Next Safe Actions
    lines.append("## 18. Next Safe Actions")
    lines.append("")
    for action in report["next_safe_actions"]:
        lines.append(f"- {action}")
    lines.append("")

    return "\n".join(lines)


def render_html(report: dict) -> str:
    """Render disposition report as standalone offline HTML."""
    md_sections = render_markdown(report)
    # Simple markdown-to-html conversion for offline use
    html_lines = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Frozen File Disposition Report</title>",
        "<style>",
        "body { font-family: monospace; max-width: 960px; margin: 2em auto; padding: 0 1em; }",
        "h1 { border-bottom: 2px solid #333; }",
        "h2 { color: #333; margin-top: 1.5em; }",
        "table { border-collapse: collapse; width: 100%; margin: 1em 0; }",
        "th, td { border: 1px solid #999; padding: 0.4em 0.8em; text-align: left; }",
        "th { background: #eee; }",
        ".safety { background: #fff3cd; padding: 1em; border: 1px solid #ffc107; }",
        ".forbidden { color: #dc3545; }",
        ".no-touch { background: #f8d7da; padding: 1em; border: 1px solid #f5c6cb; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Frozen File Disposition Report</h1>",
    ]

    # Executive Summary
    es = report["executive_summary"]
    html_lines.append("<h2>1. Executive Summary</h2>")
    html_lines.append("<ul>")
    html_lines.append(f"<li>Total frozen files: <strong>{es['total_frozen_files']}</strong></li>")
    html_lines.append(f"<li>release_hold: <strong>{html_mod.escape(str(es['release_hold']))}</strong></li>")
    html_lines.append(f"<li>advisory_only: <strong>{es['advisory_only']}</strong></li>")
    html_lines.append(f"<li>human_review_required: <strong>{es['human_review_required']}</strong></li>")
    html_lines.append("</ul>")

    # Safety Boundary
    html_lines.append("<h2>2. Safety Boundary</h2>")
    html_lines.append('<div class="safety"><ul>')
    for k, v in report["safety_boundary"].items():
        html_lines.append(f"<li><strong>{k}:</strong> {v}</li>")
    html_lines.append("</ul></div>")

    # Frozen File Count
    html_lines.append(f"<h2>3. Frozen File Count</h2><p>Total: <strong>{report['frozen_file_count']}</strong></p>")

    # Priority Breakdown
    html_lines.append("<h2>4. Priority Breakdown</h2><ul>")
    for k, v in report["priority_breakdown"].items():
        html_lines.append(f"<li><strong>{k}:</strong> {v}</li>")
    html_lines.append("</ul>")

    # Disposition Breakdown
    html_lines.append("<h2>5. Disposition Breakdown</h2><ul>")
    for k, v in report["disposition_breakdown"].items():
        html_lines.append(f"<li><strong>{k}:</strong> {v}</li>")
    html_lines.append("</ul>")

    # P0
    html_lines.append("<h2>6. P0 Critical Review Items</h2><ul>")
    for item in report["p0_critical_review_items"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}</strong> — {item['category']}, risk={item['risk_score']}</li>")
    if not report["p0_critical_review_items"]:
        html_lines.append("<li>None.</li>")
    html_lines.append("</ul>")

    # P1
    html_lines.append("<h2>7. P1 High Review Items</h2><ul>")
    for item in report["p1_high_review_items"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}</strong> — {item['category']}, risk={item['risk_score']}</li>")
    if not report["p1_high_review_items"]:
        html_lines.append("<li>None.</li>")
    html_lines.append("</ul>")

    # Archive Candidates
    html_lines.append("<h2>8. Archive Candidates</h2><ul>")
    for item in report["archive_candidates"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}</strong> — backup_required={item['backup_required']}</li>")
    if not report["archive_candidates"]:
        html_lines.append("<li>None.</li>")
    html_lines.append("</ul>")

    # Delete After Backup
    html_lines.append("<h2>9. Delete After Backup Candidates</h2><ul>")
    for item in report["delete_after_backup_candidates"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}</strong> — backup_required={item['backup_required']}</li>")
    if not report["delete_after_backup_candidates"]:
        html_lines.append("<li>None.</li>")
    html_lines.append("</ul>")

    # Offline Rewrite
    html_lines.append("<h2>10. Offline Rewrite Candidates</h2><ul>")
    for item in report["offline_rewrite_candidates"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}</strong> — backup_required={item['backup_required']}</li>")
    if not report["offline_rewrite_candidates"]:
        html_lines.append("<li>None.</li>")
    html_lines.append("</ul>")

    # Keep Frozen
    html_lines.append("<h2>11. Keep Frozen Items</h2><ul>")
    for item in report["keep_frozen_items"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}</strong></li>")
    if not report["keep_frozen_items"]:
        html_lines.append("<li>None.</li>")
    html_lines.append("</ul>")

    # Unknown
    html_lines.append("<h2>12. Unknown Items</h2><ul>")
    for item in report["unknown_items"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}</strong> — risk={item['risk_score']}</li>")
    if not report["unknown_items"]:
        html_lines.append("<li>None.</li>")
    html_lines.append("</ul>")

    # Required Human Decisions
    html_lines.append("<h2>13. Required Human Decisions</h2><ul>")
    for item in report["required_human_decisions"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}</strong> — {html_mod.escape(item['decision_placeholder'])}</li>")
    html_lines.append("</ul>")

    # Required Backup Evidence
    html_lines.append("<h2>14. Required Backup Evidence</h2><ul>")
    for item in report["required_backup_evidence"]:
        html_lines.append(f"<li><strong>{html_mod.escape(item['path'])}:</strong> {html_mod.escape(', '.join(item['evidence']))}</li>")
    if not report["required_backup_evidence"]:
        html_lines.append("<li>None.</li>")
    html_lines.append("</ul>")

    # Forbidden Actions
    html_lines.append('<h2>15. Forbidden Actions</h2><ul class="forbidden">')
    for action in report["forbidden_actions"]:
        html_lines.append(f"<li>{html_mod.escape(action)}</li>")
    html_lines.append("</ul>")

    # No-Touch Statement
    html_lines.append('<h2>16. No-Touch Statement</h2>')
    html_lines.append(f'<div class="no-touch"><p>{html_mod.escape(report["no_touch_statement"])}</p></div>')

    # release_hold HOLD
    html_lines.append(f'<h2>17. release_hold HOLD Statement</h2><p><strong>{html_mod.escape(report["release_hold_statement"])}</strong></p>')

    # Next Safe Actions
    html_lines.append("<h2>18. Next Safe Actions</h2><ul>")
    for action in report["next_safe_actions"]:
        html_lines.append(f"<li>{html_mod.escape(action)}</li>")
    html_lines.append("</ul>")

    html_lines.extend(["</body>", "</html>"])
    return "\n".join(html_lines)


def write_json(report: dict, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")


def write_manifest(report: dict, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "total_frozen_files": report["frozen_file_count"],
        "release_hold": report["executive_summary"]["release_hold"],
        "advisory_only": True,
        "human_review_required": True,
        "no_touch_required": True,
        "priority_breakdown": report["priority_breakdown"],
        "candidate_action_breakdown": report["candidate_action_breakdown"],
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(md: str, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")


def write_html(html: str, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
