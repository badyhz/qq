#!/usr/bin/env python3
"""CLI: Build historical OHLCV backtest research bundle from component files.

Reads component JSON/MD/HTML files, computes hashes, writes manifest.json
alongside them in the output directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_backtest_bundle_builder import (
    build_backtest_bundle,
    build_manifest,
    compute_sha256,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build historical OHLCV backtest research bundle"
    )
    parser.add_argument("--data-quality-json", required=True, help="Path to data quality report JSON")
    parser.add_argument("--matrix-json", required=True, help="Path to matrix JSON")
    parser.add_argument("--results-json", required=True, help="Path to results JSON")
    parser.add_argument("--scorecard-json", required=True, help="Path to scorecard JSON")
    parser.add_argument("--comparison-json", required=True, help="Path to comparison JSON")
    parser.add_argument("--report-md", required=True, help="Path to report markdown")
    parser.add_argument("--report-html", required=True, help="Path to report HTML")
    parser.add_argument("--output-dir", required=True, help="Directory to write manifest.json")
    args = parser.parse_args(argv)

    # Map artifact names -> file paths
    artifacts = {
        "data_quality_report.json": args.data_quality_json,
        "matrix.json": args.matrix_json,
        "results.json": args.results_json,
        "scorecard.json": args.scorecard_json,
        "comparison.json": args.comparison_json,
        "report.md": args.report_md,
        "report.html": args.report_html,
    }

    # Validate all artifacts exist
    for name, path_str in artifacts.items():
        if not Path(path_str).exists():
            print(f"ERROR: missing artifact {name} at {path_str}", file=sys.stderr)
            return 1

    # Build manifest
    manifest = build_backtest_bundle(
        output_dir=args.output_dir,
        artifacts_dict=artifacts,
    )

    # Verify safety flags
    assert manifest["release_hold"] == "HOLD"
    assert manifest["no_live"] is True
    assert manifest["no_submit"] is True
    assert manifest["no_exchange"] is True

    # Write manifest
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    print(f"Bundle manifest written to {manifest_path}")
    print(f"  artifacts: {manifest['artifact_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
