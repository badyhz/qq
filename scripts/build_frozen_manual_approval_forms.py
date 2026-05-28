#!/usr/bin/env python3
"""Build frozen manual approval forms from evidence checklist.

Never grants actual approval. All decisions are placeholders.

Usage:
    PYTHONPATH=. python3 scripts/build_frozen_manual_approval_forms.py \
        --backup-evidence-checklist-dir /tmp/frozen_backup_evidence_checklist \
        --output-dir /tmp/frozen_manual_approval_forms \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from core.frozen_manual_approval_form import (
    RELEASE_HOLD_REQUIRED,
    build_manual_approval_forms,
    load_checklist_items,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen manual approval forms")
    parser.add_argument("--backup-evidence-checklist-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_manual_approval_forms")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    checklist_path = pathlib.Path(args.backup_evidence_checklist_dir) / "backup_evidence_checklist.json"

    if not checklist_path.exists():
        print(f"FAIL: {checklist_path} not found.", file=sys.stderr)
        return 1

    checklist_items = load_checklist_items(checklist_path)
    forms = build_manual_approval_forms(checklist_items, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    write_json(forms, out_dir / "manual_approval_forms.json")
    write_manifest(forms, out_dir / "manual_approval_forms_manifest.json", args.release_hold)
    write_markdown(forms, out_dir / "manual_approval_forms.md")

    print(f"OK: {len(forms)} manual approval forms built")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
