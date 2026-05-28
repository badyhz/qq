#!/usr/bin/env python3
"""Render frozen archive simulation report.

Combines backup manifest, archive simulation, and verification into final report.

Usage:
    PYTHONPATH=. python3 scripts/render_frozen_archive_simulation_report.py \
        --backup-manifest-dir /tmp/frozen_backup_manifest \
        --archive-simulation-dir /tmp/frozen_archive_simulation \
        --backup-verification-dir /tmp/frozen_backup_verification \
        --output-dir /tmp/frozen_archive_simulation_report \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

from core.frozen_backup_verification import RELEASE_HOLD_REQUIRED


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render frozen archive simulation report")
    parser.add_argument("--backup-manifest-dir", required=True)
    parser.add_argument("--archive-simulation-dir", required=True)
    parser.add_argument("--backup-verification-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_archive_simulation_report")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def _load_json(path: pathlib.Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_html(report: dict) -> str:
    """Render standalone offline HTML report."""
    sections = report.get("sections", [])
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Frozen Archive Simulation Report</title>",
        "<style>",
        "body { font-family: monospace; margin: 2em; background: #1a1a2e; color: #e0e0e0; }",
        "h1 { color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 0.5em; }",
        "h2 { color: #7eb8da; margin-top: 2em; }",
        "h3 { color: #a0d2db; }",
        ".pass { color: #4caf50; }",
        ".fail { color: #f44336; }",
        ".warn { color: #ff9800; }",
        ".info { color: #2196f3; }",
        "table { border-collapse: collapse; width: 100%; margin: 1em 0; }",
        "th, td { border: 1px solid #444; padding: 0.5em; text-align: left; }",
        "th { background: #2a2a4a; }",
        "pre { background: #2a2a3e; padding: 1em; overflow-x: auto; }",
        ".safety-box { border: 2px solid #f44336; padding: 1em; margin: 1em 0; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Frozen Archive Simulation Report</h1>",
    ]

    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "")
        html_parts.append(f"<h2>{title}</h2>")
        if content:
            html_parts.append(f"<pre>{content}</pre>")

        items = section.get("items", [])
        if items:
            html_parts.append("<table>")
            if isinstance(items[0], dict):
                html_parts.append("<tr>")
                for key in items[0]:
                    html_parts.append(f"<th>{key}</th>")
                html_parts.append("</tr>")
                for item in items:
                    html_parts.append("<tr>")
                    for val in item.values():
                        html_parts.append(f"<td>{val}</td>")
                    html_parts.append("</tr>")
            else:
                for item in items:
                    html_parts.append(f"<tr><td>{item}</td></tr>")
            html_parts.append("</table>")

    html_parts.extend([
        "</body>",
        "</html>",
    ])
    return "\n".join(html_parts)


def _build_report(
    backup_items: list[dict],
    sim_items: list[dict],
    verification: dict,
    release_hold: str,
) -> dict:
    """Build the full report structure."""
    # Classify items
    backup_required = [i for i in backup_items if i.get("backup_required", False)]
    keep_frozen = [i for i in backup_items if i.get("candidate_action") == "KEEP_FROZEN"]
    needs_review = [i for i in backup_items if i.get("candidate_action") == "NEEDS_MORE_REVIEW"]
    unknown = [i for i in backup_items if i.get("backup_class") == "UNKNOWN"]

    blocked_backup = [i for i in sim_items if i.get("final_status") == "BLOCKED_PENDING_BACKUP"]
    blocked_approval = [i for i in sim_items if i.get("final_status") == "BLOCKED_PENDING_HUMAN_APPROVAL"]
    blocked_unknown = [i for i in sim_items if i.get("final_status") == "BLOCKED_UNKNOWN_RISK"]
    ready_review = [i for i in sim_items if i.get("final_status") == "SIMULATED_READY_FOR_HUMAN_REVIEW"]

    sections = [
        {
            "title": "1. Executive Summary",
            "content": (
                f"Total backup manifest items: {len(backup_items)}\n"
                f"Total simulation items: {len(sim_items)}\n"
                f"Verification checks: {verification.get('total_checks', 0)} "
                f"({verification.get('passed_checks', 0)} passed, "
                f"{verification.get('failed_checks', 0)} failed)\n"
                f"release_hold: {release_hold}\n"
                f"simulation_only: true\n"
                f"No actual file operations performed."
            ),
        },
        {
            "title": "2. Safety Boundary",
            "content": (
                "NO actual archive/delete/move/rename operations.\n"
                "NO actual backup copies created.\n"
                "NO frozen files touched/staged/executed/imported.\n"
                "release_hold = HOLD\n"
                "advisory_only = true\n"
                "human_review_required = true\n"
                "simulation_only = true"
            ),
        },
        {
            "title": "3. Backup Manifest Summary",
            "content": (
                f"Total items: {len(backup_items)}\n"
                f"Backup required: {len(backup_required)}\n"
                f"Keep frozen: {len(keep_frozen)}\n"
                f"Needs review: {len(needs_review)}\n"
                f"Unknown: {len(unknown)}"
            ),
        },
        {
            "title": "4. Archive Simulation Summary",
            "content": (
                f"Total items: {len(sim_items)}\n"
                f"Blocked pending backup: {len(blocked_backup)}\n"
                f"Blocked pending approval: {len(blocked_approval)}\n"
                f"Blocked unknown risk: {len(blocked_unknown)}\n"
                f"Ready for human review: {len(ready_review)}"
            ),
        },
        {
            "title": "5. Rollback Plan Summary",
            "content": (
                f"Total rollback items: {len(sim_items)}\n"
                "All items: forbidden_automated_restore = true\n"
                "All items: human_approval_required = true\n"
                "All items: manual restore templates are documentation only"
            ),
        },
        {
            "title": "6. Backup Verification Summary",
            "content": json.dumps(verification, indent=2),
        },
        {
            "title": "7. Files Requiring Backup",
            "content": "\n".join(
                f"  - {i['path']} ({i.get('backup_class', 'UNKNOWN')})"
                for i in backup_required
            ) or "  (none)",
        },
        {
            "title": "8. Files Blocked Pending Human Approval",
            "content": "\n".join(
                f"  - {i['path']}"
                for i in blocked_approval
            ) or "  (none)",
        },
        {
            "title": "9. Files Blocked Pending Backup",
            "content": "\n".join(
                f"  - {i['path']}"
                for i in blocked_backup
            ) or "  (none)",
        },
        {
            "title": "10. Keep Frozen Items",
            "content": "\n".join(
                f"  - {i['path']}"
                for i in keep_frozen
            ) or "  (none)",
        },
        {
            "title": "11. Unknown Risk Items",
            "content": "\n".join(
                f"  - {i['path']}"
                for i in unknown + blocked_unknown
            ) or "  (none)",
        },
        {
            "title": "12. Hypothetical Archive Paths",
            "content": "\n".join(
                f"  - {i['path']} -> {i.get('simulated_archive_path', 'N/A')}"
                for i in sim_items
            ),
        },
        {
            "title": "13. Required Hash Checks",
            "content": "\n".join(
                f"  - {i['path']}: sha256={i.get('sha256', 'N/A')}"
                for i in backup_items if i.get("sha256")
            ),
        },
        {
            "title": "14. Forbidden Actions",
            "content": (
                "The following actions are FORBIDDEN:\n"
                "- BACKUP_DONE\n- SAFE_TO_DELETE\n- SAFE_TO_MOVE\n"
                "- ARCHIVED\n- DELETED\n- MOVED\n- EXECUTED\n"
                "- IMPORTED\n- ACTIVATED\n"
                "- Any actual archive/delete/move/rename operation"
            ),
        },
        {
            "title": "15. No Actual File Operations Statement",
            "content": (
                "This report is SIMULATION ONLY.\n"
                "No files were archived, deleted, moved, renamed, or modified.\n"
                "No backup copies were created.\n"
                "All proposed paths are hypothetical."
            ),
        },
        {
            "title": "16. release_hold HOLD Statement",
            "content": (
                f"release_hold = {release_hold}\n"
                "No release action may proceed until release_hold is lifted by human operator."
            ),
        },
        {
            "title": "17. Next Safe Actions",
            "content": (
                "Recommended next phase: T16001-T16500 "
                "Offline Frozen File Backup Evidence Checklist / Manual Approval Forms\n"
                "Still no actual file movement.\n"
                "Human must review and approve each item before any action."
            ),
        },
    ]

    return {
        "sections": sections,
        "metadata": {
            "total_backup_items": len(backup_items),
            "total_simulation_items": len(sim_items),
            "release_hold": release_hold,
            "simulation_only": True,
            "advisory_only": True,
            "report_hash": hashlib.sha256(
                json.dumps(sections, sort_keys=True, indent=2).encode()
            ).hexdigest(),
        },
    }


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    backup_path = pathlib.Path(args.backup_manifest_dir) / "backup_manifest.json"
    sim_path = pathlib.Path(args.archive_simulation_dir) / "archive_simulation.json"
    verif_path = pathlib.Path(args.backup_verification_dir) / "backup_verification.json"

    if args.strict:
        for p, label in [(backup_path, "backup manifest"), (sim_path, "archive simulation"), (verif_path, "verification")]:
            if not p.exists():
                print(f"FAIL: {label} not found at {p}", file=sys.stderr)
                return 1

    backup_items = _load_json(backup_path) if backup_path.exists() else []
    sim_items = _load_json(sim_path) if sim_path.exists() else []
    verification = _load_json(verif_path) if verif_path.exists() else {}

    if isinstance(verification, dict) and "checks" in verification:
        verif_dict = verification
    else:
        verif_dict = {"checks": [], "total_checks": 0, "passed_checks": 0, "failed_checks": 0}

    report = _build_report(backup_items, sim_items, verif_dict, args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "archive_simulation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=False), encoding="utf-8"
    )

    # Markdown
    md_lines = ["# Frozen Archive Simulation Report", ""]
    for section in report["sections"]:
        md_lines.append(f"## {section['title']}")
        md_lines.append("")
        if section.get("content"):
            md_lines.append(section["content"])
        md_lines.append("")
    (out_dir / "archive_simulation_report.md").write_text("\n".join(md_lines), encoding="utf-8")

    # HTML
    (out_dir / "archive_simulation_report.html").write_text(
        _render_html(report), encoding="utf-8"
    )

    # Manifest
    manifest = {
        "total_sections": len(report["sections"]),
        "metadata": report["metadata"],
        "release_hold": args.release_hold,
        "simulation_only": True,
    }
    (out_dir / "archive_simulation_report_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"OK: archive simulation report rendered ({len(report['sections'])} sections)")
    print(f"    release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
