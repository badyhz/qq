#!/usr/bin/env python3
"""T1855 - CLI to build frozen backlog review board packet bundle.

Generates all artifacts into --output-dir:
  - report.md, report.json, validation.json, validation.md
  - snapshot.json, dashboard.html, board_packet.md, manifest.json

Usage:
    python scripts/build_frozen_backlog_review_bundle.py --output-dir DIR

Exit 0 on success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_report_renderer import render_report_markdown
from core.frozen_backlog_report_json import render_report_json
from core.frozen_backlog_report_validator import validate_report_data
from core.frozen_backlog_dashboard_renderer import render_dashboard_html
from core.frozen_backlog_board_packet_renderer import render_board_packet_md


def _sha256_file(path: str) -> str:
    """Compute sha256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _render_validation_md(is_valid: bool, passed: tuple[str, ...], failed: tuple[str, ...], error_msg: str) -> str:
    """Render validation result as markdown."""
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build frozen backlog review board packet bundle",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for all artifacts",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Generate report data
    summary, records = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
    report_json_str = render_report_json(summary, records)
    report_data = json.loads(report_json_str)

    # Validate
    validation = validate_report_data(report_data)
    validation_dict = {
        "is_valid": validation.is_valid,
        "checks_passed": list(validation.checks_passed),
        "checks_failed": list(validation.checks_failed),
        "error_message": validation.error_message,
    }

    # Build snapshot
    snapshot = {
        "inventory_id": FROZEN_BACKLOG_INVENTORY.inventory_id,
        "total_count": FROZEN_BACKLOG_INVENTORY.total_count,
        "high_risk_count": FROZEN_BACKLOG_INVENTORY.high_risk_count,
        "medium_risk_count": FROZEN_BACKLOG_INVENTORY.medium_risk_count,
        "release_hold": "HOLD",
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
    }

    # Render artifacts
    report_md = render_report_markdown(summary, records)
    validation_md = _render_validation_md(
        validation.is_valid,
        validation.checks_passed,
        validation.checks_failed,
        validation.error_message,
    )
    dashboard_html = render_dashboard_html(summary, records)
    board_packet_md = render_board_packet_md(summary, records, validation)

    # Write all artifacts
    artifacts: dict[str, str] = {
        "report.md": report_md,
        "report.json": report_json_str,
        "validation.json": json.dumps(validation_dict, sort_keys=True, indent=2),
        "validation.md": validation_md,
        "snapshot.json": json.dumps(snapshot, sort_keys=True, indent=2),
        "dashboard.html": dashboard_html,
        "board_packet.md": board_packet_md,
    }

    artifact_paths: list[str] = []
    for filename, content in artifacts.items():
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        artifact_paths.append(path)

    # Build manifest
    manifest_artifacts: list[dict[str, object]] = []
    for path in artifact_paths:
        size = os.path.getsize(path)
        sha = _sha256_file(path)
        manifest_artifacts.append({
            "filename": os.path.basename(path),
            "size_bytes": size,
            "sha256_hash": sha,
        })

    manifest = {
        "generated_by": "frozen_backlog_review_platform",
        "release_hold": "HOLD",
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "artifacts": manifest_artifacts,
    }

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, sort_keys=True, indent=2)
        f.write("\n")

    print(f"Bundle written to {output_dir}")
    print(f"Artifacts: {len(artifacts) + 1} files (including manifest.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
