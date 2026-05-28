#!/usr/bin/env python3
"""Validate offline research experiment library.

No network. No exchange. No runtime. No planner. Advisory only.
release_hold must remain HOLD.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.offline_research_experiment_validator import validate_catalog_strict
from core.offline_research_experiment_manifest import generate_full_manifest, save_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate offline research experiment library"
    )
    parser.add_argument(
        "--catalog", required=True, type=Path,
        help="Path to experiment_catalog.json"
    )
    parser.add_argument(
        "--output-dir", required=True, type=Path,
        help="Output directory for validation results"
    )
    parser.add_argument(
        "--strict", action="store_true", default=False,
        help="Enable strict validation mode"
    )
    parser.add_argument(
        "--release-hold", default="HOLD", type=str,
        help="Expected release_hold value (must be HOLD)"
    )
    parser.add_argument(
        "--min-experiments", default=20, type=int,
        help="Minimum number of experiments required"
    )
    args = parser.parse_args()

    if args.release_hold != "HOLD":
        print(f"ERROR: release_hold must be HOLD, got {args.release_hold}", file=sys.stderr)
        return 1

    if not args.catalog.is_file():
        print(f"ERROR: Catalog file not found: {args.catalog}", file=sys.stderr)
        return 1

    result = validate_catalog_strict(
        args.catalog,
        release_hold=args.release_hold,
        min_experiments=args.min_experiments,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Save validation result
    validation_path = args.output_dir / "experiment_library_validation.json"
    with open(validation_path, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)

    # Save manifest
    if result.get("manifest"):
        manifest_path = args.output_dir / "experiment_library_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(result["manifest"], f, indent=2, sort_keys=True)

    # Generate full manifest
    try:
        full_manifest = generate_full_manifest(args.catalog)
        save_manifest(full_manifest, args.output_dir / "experiment_full_manifest.json")
    except Exception as e:
        print(f"WARNING: Could not generate full manifest: {e}", file=sys.stderr)

    if result["valid"]:
        print(f"PASS: {result['total_experiments']} experiments validated")
        return 0
    else:
        print(f"FAIL: {len(result['errors'])} errors found", file=sys.stderr)
        for err in result["errors"]:
            print(f"  - {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
