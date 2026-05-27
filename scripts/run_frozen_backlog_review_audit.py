#!/usr/bin/env python3
"""T1625 - Frozen Backlog Review Audit Orchestrator.

Orchestrates: generate -> validate -> diff (optional) -> write outputs.
Deterministic. No network. No exchange. No frozen file imports.
Exit 0 if validation PASS, 1 if FAIL.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_json import render_report_json, render_summary_dict
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_report_renderer import render_report_markdown, render_summary_markdown
from core.frozen_backlog_report_validator import validate_report_data


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Frozen backlog review audit orchestrator."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to write all output files.",
    )
    parser.add_argument(
        "--mode",
        choices=("summary", "full"),
        default="full",
        help="Report mode: summary or full (default full).",
    )
    parser.add_argument(
        "--snapshot",
        type=str,
        default=None,
        help="Path to previous snapshot/report JSON for diff.",
    )
    return parser.parse_args(argv)


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def _extract_report_data(data: dict) -> dict:
    """Extract report_data from snapshot or use raw report."""
    if "report_data" in data:
        return data["report_data"]
    return data


def _build_record_map(records: list[dict]) -> dict[str, dict]:
    return {r["file_path"]: r for r in records}


def _diff_reports(before: dict, after: dict) -> dict:
    """Compute diff between two report dicts. Pure function."""
    before_data = _extract_report_data(before)
    after_data = _extract_report_data(after)

    before_records = before_data.get("records", [])
    after_records = after_data.get("records", [])

    before_map = _build_record_map(before_records)
    after_map = _build_record_map(after_records)

    before_paths = set(before_map.keys())
    after_paths = set(after_map.keys())

    added_files = sorted(after_paths - before_paths)
    removed_files = sorted(before_paths - after_paths)
    common_paths = sorted(before_paths & after_paths)

    field_changes = []
    tracked_fields = [
        "risk_class", "category", "unlock_recommendation", "release_hold",
    ]

    for fp in common_paths:
        brec = before_map[fp]
        arec = after_map[fp]
        for field in tracked_fields:
            old_val = brec.get(field)
            new_val = arec.get(field)
            if old_val != new_val:
                field_changes.append({
                    "file_path": fp,
                    "field_name": field,
                    "old_value": old_val,
                    "new_value": new_val,
                })

    before_summary = before_data.get("summary", {})
    after_summary = after_data.get("summary", {})
    summary_changes = []
    summary_fields = [
        "total_files", "high_risk_count", "medium_risk_count", "release_hold",
        "no_live", "no_submit", "no_exchange", "no_runtime_integration",
        "no_planner_integration",
    ]
    for field in summary_fields:
        old_val = before_summary.get(field)
        new_val = after_summary.get(field)
        if old_val != new_val:
            summary_changes.append({
                "field_name": field,
                "old_value": old_val,
                "new_value": new_val,
            })

    has_changes = bool(added_files or removed_files or field_changes or summary_changes)

    return {
        "has_changes": has_changes,
        "added_files": added_files,
        "removed_files": removed_files,
        "field_changes": field_changes,
        "summary_changes": summary_changes,
        "total_changes": len(added_files) + len(removed_files) + len(field_changes) + len(summary_changes),
    }


def _render_diff_md(diff: dict, before_path: str, after_path: str) -> str:
    lines = [
        "# Frozen Backlog Diff Report",
        "",
        f"- **Before:** {before_path}",
        f"- **After:** {after_path}",
        f"- **Has changes:** {diff['has_changes']}",
        f"- **Total changes:** {diff['total_changes']}",
        "",
    ]

    if diff["summary_changes"]:
        lines.append("## Summary Changes")
        lines.append("")
        for ch in diff["summary_changes"]:
            lines.append(f"- **{ch['field_name']}**: `{ch['old_value']}` -> `{ch['new_value']}`")
        lines.append("")

    if diff["added_files"]:
        lines.append("## Added Files")
        lines.append("")
        for fp in diff["added_files"]:
            lines.append(f"- `{fp}`")
        lines.append("")

    if diff["removed_files"]:
        lines.append("## Removed Files")
        lines.append("")
        for fp in diff["removed_files"]:
            lines.append(f"- `{fp}`")
        lines.append("")

    if diff["field_changes"]:
        lines.append("## Record Field Changes")
        lines.append("")
        for ch in diff["field_changes"]:
            lines.append(
                f"- `{ch['file_path']}` **{ch['field_name']}**: "
                f"`{ch['old_value']}` -> `{ch['new_value']}`"
            )
        lines.append("")

    if not diff["has_changes"]:
        lines.append("No changes detected.")
        lines.append("")

    return "\n".join(lines)


def _render_audit_summary_md(
    mode: str,
    validation_passed: bool,
    diff_result: dict | None,
    output_files: list[str],
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Frozen Backlog Audit Summary",
        "",
        f"- **Timestamp (UTC):** {ts}",
        f"- **Mode:** {mode}",
        f"- **Validation:** {'PASS' if validation_passed else 'FAIL'}",
    ]

    if diff_result is not None:
        lines.append(f"- **Diff snapshot:** provided")
        lines.append(f"- **Diff has changes:** {diff_result['has_changes']}")
        lines.append(f"- **Diff total changes:** {diff_result['total_changes']}")
    else:
        lines.append(f"- **Diff snapshot:** not provided")

    lines.append("")
    lines.append("## Output Files")
    lines.append("")
    for f in sorted(output_files):
        lines.append(f"- `{f}`")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_files: list[str] = []

    # --- Step 1: Generate report ---
    inventory = FROZEN_BACKLOG_INVENTORY
    summary, records = materialize_full_report(inventory)

    md_path = out_dir / "frozen_backlog_review.md"
    json_path = out_dir / "frozen_backlog_review.json"

    if args.mode == "full":
        md_content = render_report_markdown(summary, records)
        json_content = render_report_json(summary, records)
    else:
        md_content = render_summary_markdown(summary)
        json_content = json.dumps(
            {"summary": render_summary_dict(summary)},
            sort_keys=True,
            indent=2,
        )

    _write_file(md_path, md_content)
    _write_file(json_path, json_content)
    output_files.extend([str(md_path), str(json_path)])

    # --- Step 2: Validate report ---
    report_data = json.loads(json_content)
    result = validate_report_data(report_data)
    validation_passed = result.is_valid

    validation_lines = [
        f"Checks passed: {len(result.checks_passed)}",
        f"Checks failed: {len(result.checks_failed)}",
    ]
    if result.error_message:
        validation_lines.append(f"Error: {result.error_message}")
    validation_lines.append(f"Result: {'PASS' if validation_passed else 'FAIL'}")

    val_path = out_dir / "frozen_backlog_validation.txt"
    _write_file(val_path, "\n".join(validation_lines) + "\n")
    output_files.append(str(val_path))

    # --- Step 3: Diff (optional) ---
    diff_result: dict | None = None
    if args.snapshot:
        try:
            before_data = _load_json(args.snapshot)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"ERROR loading snapshot: {exc}", file=sys.stderr)
            return 1

        diff_result = _diff_reports(before_data, report_data)

        diff_md_path = out_dir / "frozen_backlog_diff.md"
        diff_json_path = out_dir / "frozen_backlog_diff.json"

        diff_md_content = _render_diff_md(diff_result, args.snapshot, str(json_path))
        diff_json_content = json.dumps(diff_result, indent=2, sort_keys=True) + "\n"

        _write_file(diff_md_path, diff_md_content)
        _write_file(diff_json_path, diff_json_content)
        output_files.extend([str(diff_md_path), str(diff_json_path)])

    # --- Step 4: Write audit summary ---
    audit_summary = _render_audit_summary_md(
        args.mode, validation_passed, diff_result, output_files,
    )
    audit_path = out_dir / "frozen_backlog_audit_summary.md"
    _write_file(audit_path, audit_summary)
    output_files.append(str(audit_path))

    # --- Print deterministic summary to stdout ---
    print(f"Mode: {args.mode}")
    print(f"Files: {inventory.total_count}")
    print(f"Validation: {'PASS' if validation_passed else 'FAIL'}")
    print(f"Checks passed: {len(result.checks_passed)}")
    print(f"Checks failed: {len(result.checks_failed)}")
    if diff_result is not None:
        print(f"Diff has changes: {diff_result['has_changes']}")
        print(f"Diff total changes: {diff_result['total_changes']}")
    print(f"Output dir: {out_dir}")
    print(f"Output files: {len(output_files)}")

    return 0 if validation_passed else 1


if __name__ == "__main__":
    sys.exit(main())
