#!/usr/bin/env python3
"""Render frozen completed form report.

Renders comprehensive report from simulation, validation, and matrix data.
No actual approval. No file operations. Dry-run only.

Usage:
    PYTHONPATH=. python3 scripts/render_frozen_completed_form_report.py \
        --completed-form-simulations-dir /tmp/frozen_completed_form_simulations \
        --dry-run-validation-dir /tmp/frozen_approval_dry_run_validation \
        --outcome-matrix-dir /tmp/frozen_approval_outcome_matrix \
        --output-dir /tmp/frozen_completed_form_report \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_completed_form_report import (
    RELEASE_HOLD_REQUIRED,
    render_manifest,
    render_report_html,
    render_report_json,
    render_report_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render frozen completed form report")
    parser.add_argument("--completed-form-simulations-dir", required=True)
    parser.add_argument("--dry-run-validation-dir", required=True)
    parser.add_argument("--outcome-matrix-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_completed_form_report")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    sims_path = pathlib.Path(args.completed_form_simulations_dir) / "completed_form_simulations.json"
    val_path = pathlib.Path(args.dry_run_validation_dir) / "dry_run_validation.json"
    mat_path = pathlib.Path(args.outcome_matrix_dir) / "approval_outcome_matrix.json"

    for p in (sims_path, val_path, mat_path):
        if not p.exists():
            print(f"FAIL: {p} not found.", file=sys.stderr)
            return 1

    sims = json.loads(sims_path.read_text(encoding="utf-8"))
    val = json.loads(val_path.read_text(encoding="utf-8"))
    mat = json.loads(mat_path.read_text(encoding="utf-8"))

    report = render_report_json(sims, val, mat, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "completed_form_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (out_dir / "completed_form_report.md").write_text(
        render_report_markdown(report), encoding="utf-8"
    )
    (out_dir / "completed_form_report.html").write_text(
        render_report_html(report), encoding="utf-8"
    )
    (out_dir / "completed_form_report_manifest.json").write_text(
        json.dumps(render_manifest(report), indent=2), encoding="utf-8"
    )

    print(f"OK: report rendered with {len(report.get('sections', {}))} sections")
    print(f"    release_hold={args.release_hold}")
    print(f"    action_authorized=False")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
