#!/usr/bin/env python3
"""Build frozen completed form simulations.

Reads manual approval forms and generates simulated completed forms.
No actual approval. No file operations. Dry-run only.

Usage:
    PYTHONPATH=. python3 scripts/build_frozen_completed_form_simulations.py \
        --manual-approval-forms-dir /tmp/frozen_manual_approval_forms \
        --backup-evidence-checklist-dir /tmp/frozen_backup_evidence_checklist \
        --output-dir /tmp/frozen_completed_form_simulations \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_completed_form_simulation import (
    RELEASE_HOLD_REQUIRED,
    generate_simulations,
    render_manifest,
    render_simulation_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen completed form simulations")
    parser.add_argument("--manual-approval-forms-dir", required=True)
    parser.add_argument("--backup-evidence-checklist-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_completed_form_simulations")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    forms_path = pathlib.Path(args.manual_approval_forms_dir) / "manual_approval_forms.json"
    if not forms_path.exists():
        print(f"FAIL: {forms_path} not found.", file=sys.stderr)
        return 1

    forms = json.loads(forms_path.read_text(encoding="utf-8"))
    if not isinstance(forms, list):
        forms = forms.get("items", [])

    result = generate_simulations(forms, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "completed_form_simulations.json").write_text(
        json.dumps(result.to_dict(), indent=2), encoding="utf-8"
    )
    (out_dir / "completed_form_simulations.md").write_text(
        render_simulation_markdown(result), encoding="utf-8"
    )
    (out_dir / "completed_form_simulations_manifest.json").write_text(
        json.dumps(render_manifest(result), indent=2), encoding="utf-8"
    )

    print(f"OK: {result.total_count} simulations, {len(result.category_counts)} categories")
    print(f"    release_hold={args.release_hold}")
    print(f"    dry_run_only={result.dry_run_only}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
