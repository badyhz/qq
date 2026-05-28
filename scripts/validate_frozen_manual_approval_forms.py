#!/usr/bin/env python3
"""Validate frozen manual approval forms.

Validates generated templates. No actual approval granted.

Usage:
    PYTHONPATH=. python3 scripts/validate_frozen_manual_approval_forms.py \
        --manual-approval-forms-dir /tmp/frozen_manual_approval_forms \
        --backup-evidence-checklist-dir /tmp/frozen_backup_evidence_checklist \
        --output-dir /tmp/frozen_approval_validation \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from core.frozen_approval_validator import (
    RELEASE_HOLD_REQUIRED,
    load_forms,
    validate_forms,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate frozen manual approval forms")
    parser.add_argument("--manual-approval-forms-dir", required=True)
    parser.add_argument("--backup-evidence-checklist-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_approval_validation")
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

    forms = load_forms(forms_path)
    report = validate_forms(forms, release_hold=args.release_hold, completed=False)

    out_dir = pathlib.Path(args.output_dir)
    write_json(report, out_dir / "approval_validation.json")
    write_manifest(report, out_dir / "approval_validation_manifest.json")
    write_markdown(report, out_dir / "approval_validation.md")

    print(f"OK: {report.total_checks} validation checks, {report.passed_checks} passed")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    all_passed={report.all_passed}")
    print(f"    output: {out_dir}")
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
