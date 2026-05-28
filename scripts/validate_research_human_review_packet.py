#!/usr/bin/env python3
"""Validate research human review packet — safety and signoff validation.

Usage:
    python3 scripts/validate_research_human_review_packet.py \
        --review-dir /tmp/research_human_review_packet \
        --strict \
        --release-hold HOLD

Safety: offline only. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_review_packet import validate_review_packet_safety
from core.research_review_signoff import (
    validate_completed_signoff,
    validate_signoff_template_safety,
)
from core.research_review_manifest import validate_review_manifest_safety


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate research human review packet")
    parser.add_argument("--review-dir", required=True, help="Review packet directory")
    parser.add_argument("--strict", action="store_true", help="Strict mode")
    parser.add_argument("--release-hold", default="HOLD", help="Expected release_hold value")
    args = parser.parse_args()

    if args.release_hold != "HOLD":
        print(f"FAIL: release_hold must be HOLD, got {args.release_hold}", file=sys.stderr)
        return 2

    review_dir = Path(args.review_dir)
    if not review_dir.exists():
        print(f"FAIL: review directory not found: {review_dir}", file=sys.stderr)
        return 2

    errors: list[str] = []

    # 1. Validate review_packet.json
    packet_path = review_dir / "review_packet.json"
    if not packet_path.exists():
        errors.append("review_packet.json missing")
    else:
        try:
            packet = json.loads(packet_path.read_text())
            valid, errs = validate_review_packet_safety(packet)
            if not valid:
                errors.extend([f"packet: {e}" for e in errs])
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"review_packet.json corrupted: {e}")

    # 2. Validate review_manifest.json
    manifest_path = review_dir / "review_manifest.json"
    if not manifest_path.exists():
        errors.append("review_manifest.json missing")
    else:
        try:
            manifest = json.loads(manifest_path.read_text())
            valid, errs = validate_review_manifest_safety(manifest)
            if not valid:
                errors.extend([f"manifest: {e}" for e in errs])
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"review_manifest.json corrupted: {e}")

    # 3. Validate signoff template safety
    signoff_template_path = review_dir / "review_signoff_template.json"
    if signoff_template_path.exists():
        try:
            template = json.loads(signoff_template_path.read_text())
            valid, errs = validate_signoff_template_safety(template)
            if not valid:
                errors.extend([f"signoff_template: {e}" for e in errs])
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"review_signoff_template.json corrupted: {e}")

    # 4. If completed signoff exists, validate it
    completed_signoff_path = review_dir / "review_signoff_completed.json"
    if completed_signoff_path.exists():
        try:
            completed = json.loads(completed_signoff_path.read_text())
            valid, errs = validate_completed_signoff(completed)
            if not valid:
                errors.extend([f"completed_signoff: {e}" for e in errs])
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"review_signoff_completed.json corrupted: {e}")

    # Summary
    if errors:
        print(f"FAIL: {len(errors)} validation errors:")
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    print("PASS: review packet validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
