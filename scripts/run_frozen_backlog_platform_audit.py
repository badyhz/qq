#!/usr/bin/env python3
"""T1871-T1880 - Frozen Backlog Platform Audit Runner.

Comprehensive CLI that runs the full audit pipeline end-to-end:
  1. Generates report from FROZEN_BACKLOG_INVENTORY
  2. Validates report
  3. Creates snapshot
  4. Renders dashboard HTML
  5. Builds full bundle (report.md, report.json, validation.json,
     validation.md, snapshot.json, dashboard.html, board_packet.md, manifest.json)
  6. Verifies manifest hashes match actual files
  7. Prints PASS/PARTIAL/FAIL
  8. Exits 0 only on PASS

Usage:
    python scripts/run_frozen_backlog_platform_audit.py --output-dir DIR [--mode full|summary]

Exit 0 on PASS, 1 on PARTIAL/FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_report_renderer import (
    render_report_markdown,
    render_summary_markdown,
)
from core.frozen_backlog_report_json import (
    render_report_json,
    render_summary_dict,
)
from core.frozen_backlog_report_validator import validate_report_data
from core.frozen_backlog_snapshot_manager import (
    create_snapshot,
    snapshot_to_dict,
    write_snapshot,
)
from core.frozen_backlog_dashboard_renderer import render_dashboard_html
from core.frozen_backlog_board_packet_renderer import render_board_packet_md
from core.frozen_backlog_manifest_builder import build_manifest


EXPECTED_FILES = (
    "report.md",
    "report.json",
    "validation.json",
    "validation.md",
    "snapshot.json",
    "dashboard.html",
    "board_packet.md",
    "manifest.json",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _render_validation_md(
    is_valid: bool,
    passed: tuple[str, ...],
    failed: tuple[str, ...],
    error_msg: str,
) -> str:
    lines: list[str] = []
    lines.append("# Frozen Backlog Report Validation")
    lines.append("")
    status = "PASS" if is_valid else "FAIL"
    lines.append(f"**Status:** {status}")
    lines.append("")
    lines.append(f"**Checks Passed:** {len(passed)}")
    for check in passed:
        lines.append(f"- PASS: {check}")
    lines.append("")
    lines.append(f"**Checks Failed:** {len(failed)}")
    for check in failed:
        lines.append(f"- FAIL: {check}")
    if error_msg:
        lines.append("")
        lines.append(f"**Error:** {error_msg}")
    return "\n".join(lines)


def run_platform_audit(
    output_dir: str,
    mode: str = "full",
    snapshot_path: str | None = None,
) -> int:
    """Run the full platform audit. Returns exit code (0=PASS, 1=PARTIAL/FAIL)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    inventory = FROZEN_BACKLOG_INVENTORY
    summary, records = materialize_full_report(inventory)
    steps_passed: list[str] = []
    steps_failed: list[str] = []

    # --- Step 1: Generate report ---
    # JSON always includes full data for validation.
    # Markdown is mode-dependent.
    report_json_str = render_report_json(summary, records)
    if mode == "full":
        report_md = render_report_markdown(summary, records)
    else:
        report_md = render_summary_markdown(summary)

    (out / "report.md").write_text(report_md, encoding="utf-8")
    (out / "report.json").write_text(report_json_str, encoding="utf-8")
    steps_passed.append("generate_report")

    # --- Step 2: Validate report ---
    report_data = json.loads(report_json_str)
    validation = validate_report_data(report_data)
    validation_dict = {
        "is_valid": validation.is_valid,
        "checks_passed": list(validation.checks_passed),
        "checks_failed": list(validation.checks_failed),
        "error_message": validation.error_message,
    }
    (out / "validation.json").write_text(
        json.dumps(validation_dict, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    validation_md = _render_validation_md(
        validation.is_valid,
        validation.checks_passed,
        validation.checks_failed,
        validation.error_message,
    )
    (out / "validation.md").write_text(validation_md, encoding="utf-8")

    if validation.is_valid:
        steps_passed.append("validate_report")
    else:
        steps_failed.append("validate_report")

    # --- Step 3: Create snapshot ---
    from datetime import datetime, timezone

    snap = create_snapshot(
        report_data=report_data,
        version="v1",
        created_at_iso=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        snapshot_id=f"snapshot-{inventory.inventory_id}",
    )
    snap_path = out / "snapshot.json"
    write_snapshot(snap, str(snap_path))
    steps_passed.append("create_snapshot")

    # --- Step 4: Render dashboard HTML ---
    dashboard_html = render_dashboard_html(summary, records)
    (out / "dashboard.html").write_text(dashboard_html, encoding="utf-8")
    steps_passed.append("render_dashboard")

    # --- Step 5: Build board packet ---
    board_packet_md = render_board_packet_md(summary, records, validation)
    (out / "board_packet.md").write_text(board_packet_md, encoding="utf-8")
    steps_passed.append("build_board_packet")

    # --- Step 6: Build manifest ---
    artifact_paths = tuple(
        str(out / fname)
        for fname in EXPECTED_FILES
        if fname != "manifest.json"
    )
    manifest = build_manifest(
        artifact_paths=artifact_paths,
        generated_by="frozen_backlog_platform_audit",
    )
    manifest_path = out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    steps_passed.append("build_manifest")

    # --- Step 7: Verify manifest hashes ---
    manifest_dict = json.loads(manifest_path.read_text(encoding="utf-8"))
    hash_mismatches: list[str] = []
    for entry in manifest_dict.get("artifacts", []):
        fname = entry["filename"]
        expected_hash = entry["sha256_hash"]
        actual_path = out / fname
        if actual_path.exists():
            actual_hash = _sha256_file(actual_path)
            if actual_hash != expected_hash:
                hash_mismatches.append(fname)
        else:
            hash_mismatches.append(f"{fname} (missing)")

    if not hash_mismatches:
        steps_passed.append("verify_manifest_hashes")
    else:
        steps_failed.append(f"verify_manifest_hashes:{hash_mismatches}")

    # --- Step 8: Check all expected files exist ---
    missing_files = [f for f in EXPECTED_FILES if not (out / f).exists()]
    if not missing_files:
        steps_passed.append("all_files_present")
    else:
        steps_failed.append(f"missing_files:{missing_files}")

    # --- Step 9: Snapshot diff (optional) ---
    if snapshot_path:
        snap_p = Path(snapshot_path)
        if snap_p.exists():
            try:
                old_data = json.loads(snap_p.read_text(encoding="utf-8"))
                old_report = old_data.get("report_data", old_data)
                old_records = {
                    r["file_path"]: r
                    for r in old_report.get("records", [])
                }
                new_records = {
                    r.file_path: r
                    for r in records
                }
                changes = 0
                for fp in set(old_records) | set(new_records):
                    if fp not in old_records or fp not in new_records:
                        changes += 1
                if changes == 0:
                    steps_passed.append("snapshot_diff")
                else:
                    steps_passed.append(f"snapshot_diff:{changes}_changes")
            except (json.JSONDecodeError, KeyError) as exc:
                steps_failed.append(f"snapshot_diff_error:{exc}")
        else:
            steps_failed.append(f"snapshot_diff_missing:{snapshot_path}")

    # --- Determine verdict ---
    verdict = "PASS" if not steps_failed else "PARTIAL"
    if not steps_passed:
        verdict = "FAIL"

    print(f"Mode: {mode}")
    print(f"Inventory: {inventory.total_count} files")
    print(f"Validation: {'PASS' if validation.is_valid else 'FAIL'}")
    print(f"Steps passed: {len(steps_passed)}")
    print(f"Steps failed: {len(steps_failed)}")
    print(f"Output dir: {out}")
    print(f"Output files: {len(EXPECTED_FILES)}")
    print(f"Verdict: {verdict}")

    return 0 if verdict == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Frozen backlog platform audit runner",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for all artifacts",
    )
    parser.add_argument(
        "--mode",
        choices=("summary", "full"),
        default="full",
        help="Report mode (default: full)",
    )
    parser.add_argument(
        "--snapshot",
        default=None,
        help="Path to previous snapshot JSON for diff",
    )
    args = parser.parse_args()
    return run_platform_audit(args.output_dir, args.mode, args.snapshot)


if __name__ == "__main__":
    sys.exit(main())
