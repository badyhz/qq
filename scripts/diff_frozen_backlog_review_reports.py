#!/usr/bin/env python3
"""T1621 - Frozen Backlog Diff CLI.

Diffs two report/snapshot JSONs. Writes markdown and JSON diff output.
Deterministic. No network. No subprocess. No frozen file imports.
Exit 0 on success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diff two frozen backlog report/snapshot JSONs."
    )
    parser.add_argument(
        "--before-json",
        type=str,
        required=True,
        help="Path to 'before' report/snapshot JSON.",
    )
    parser.add_argument(
        "--after-json",
        type=str,
        required=True,
        help="Path to 'after' report/snapshot JSON.",
    )
    parser.add_argument(
        "--output-md",
        type=str,
        default=None,
        help="Path to write markdown diff output.",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Path to write JSON diff output.",
    )
    return parser.parse_args(argv)


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
    """Build a dict mapping file_path -> record for fast lookup."""
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

    # Summary-level diff
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
    """Render diff as markdown. Pure function."""
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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        before = _load_json(args.before_json)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR reading before: {exc}", file=sys.stderr)
        return 1

    try:
        after = _load_json(args.after_json)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR reading after: {exc}", file=sys.stderr)
        return 1

    diff = _diff_reports(before, after)

    # Write markdown output
    if args.output_md:
        md_content = _render_diff_md(diff, args.before_json, args.after_json)
        out = Path(args.output_md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md_content, encoding="utf-8")
        print(f"Markdown diff written to {args.output_md}")

    # Write JSON output
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(diff, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"JSON diff written to {args.output_json}")

    # Print summary
    print(f"Changes detected: {diff['has_changes']}")
    print(f"Total changes: {diff['total_changes']}")
    print(f"  Added files: {len(diff['added_files'])}")
    print(f"  Removed files: {len(diff['removed_files'])}")
    print(f"  Field changes: {len(diff['field_changes'])}")
    print(f"  Summary changes: {len(diff['summary_changes'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
