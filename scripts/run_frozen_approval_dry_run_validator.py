#!/usr/bin/env python3
"""Run frozen approval dry-run validator.

Validates completed form simulations. No actual approval. Dry-run only.

Usage:
    PYTHONPATH=. python3 scripts/run_frozen_approval_dry_run_validator.py \
        --completed-form-simulations-dir /tmp/frozen_completed_form_simulations \
        --output-dir /tmp/frozen_approval_dry_run_validation \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_approval_dry_run_validator import (
    RELEASE_HOLD_REQUIRED,
    render_manifest,
    render_validation_markdown,
    validate_forms,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run frozen approval dry-run validator")
    parser.add_argument("--completed-form-simulations-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_approval_dry_run_validation")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    sims_path = pathlib.Path(args.completed_form_simulations_dir) / "completed_form_simulations.json"
    if not sims_path.exists():
        print(f"FAIL: {sims_path} not found.", file=sys.stderr)
        return 1

    data = json.loads(sims_path.read_text(encoding="utf-8"))
    forms = data.get("simulations", data) if isinstance(data, dict) else data

    validation = validate_forms(forms, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "dry_run_validation.json").write_text(
        json.dumps(validation.to_dict(), indent=2), encoding="utf-8"
    )
    (out_dir / "dry_run_validation.md").write_text(
        render_validation_markdown(validation), encoding="utf-8"
    )
    (out_dir / "dry_run_validation_manifest.json").write_text(
        json.dumps(render_manifest(validation), indent=2), encoding="utf-8"
    )

    print(f"OK: {validation.total_count} forms validated")
    print(f"    accepted={validation.accepted_count}, rejected={validation.rejected_count}, needs_review={validation.needs_review_count}")
    print(f"    release_hold={args.release_hold}")
    print(f"    action_authorized={validation.action_authorized}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
