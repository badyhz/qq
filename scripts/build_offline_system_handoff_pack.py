#!/usr/bin/env python3
"""Build offline system handoff pack.

Creates a next-window handoff pack for future conversations.
No network. No exchange. No runtime. No planner.

Usage:
    python3 scripts/build_offline_system_handoff_pack.py \
        --output-dir /tmp/offline_system_handoff_pack \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from core.offline_system_handoff_pack import (
    RELEASE_HOLD_REQUIRED,
    build_handoff_pack,
    validate_required_fields,
    validate_safety_flags,
    validate_no_activation,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
    write_next_window_prompt,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build offline system handoff pack")
    parser.add_argument("--output-dir", default="/tmp/offline_system_handoff_pack")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    pack = build_handoff_pack(repo_root=repo_root, release_hold=args.release_hold)

    if args.strict:
        missing = validate_required_fields(pack)
        if missing:
            print(f"FAIL: missing required fields: {missing}", file=sys.stderr)
            return 1
        safety_violations = validate_safety_flags(pack)
        if safety_violations:
            print(f"FAIL: safety violations: {safety_violations}", file=sys.stderr)
            return 1
        activation_violations = validate_no_activation(pack)
        if activation_violations:
            print(f"FAIL: activation violations: {activation_violations}", file=sys.stderr)
            return 1

    out_dir = pathlib.Path(args.output_dir)
    write_json(pack, out_dir / "handoff_pack.json")
    write_manifest(pack, out_dir / "handoff_pack_manifest.json")
    write_markdown(pack, out_dir / "handoff_pack.md")
    write_next_window_prompt(pack, out_dir / "next_window_prompt.md")

    print(f"OK: handoff pack generated")
    print(f"    HEAD: {pack.current_head}")
    print(f"    stages: {len(pack.completed_stages)}")
    print(f"    frozen files: {len(pack.frozen_file_list)}")
    print(f"    release_hold={pack.manifest['release_hold']}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
