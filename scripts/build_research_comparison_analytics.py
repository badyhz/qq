#!/usr/bin/env python3
"""Build research comparison analytics — full comparison pipeline.

Usage:
    python3 scripts/build_research_comparison_analytics.py \
        --bundle baseline=/tmp/research_artifact_browser \
        --bundle candidate=/tmp/research_artifact_browser_rerun \
        --output-dir /tmp/research_comparison_analytics \
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

from core.research_bundle_series import (
    build_bundle_series_index,
    load_bundle_series,
)
from core.research_comparison_metrics import (
    build_extracted_metrics_json,
    extract_metrics_from_records,
)
from core.research_comparison_pairwise import (
    build_pairwise_comparison_json,
    compare_all_pairs,
)
from core.research_comparison_regression import (
    detect_regressions,
    regression_report_to_dict,
)
from core.research_comparison_report import (
    render_comparison_html,
    render_comparison_markdown,
)
from core.research_comparison_scorecard import (
    build_scorecard,
    scorecard_to_dict,
)
from core.research_trend_engine import (
    compute_trend_report,
    trend_report_to_dict,
)
from core.research_comparison_manifest import (
    build_comparison_manifest,
    compute_bundle_hashes,
    compute_output_artifact_hashes,
    validate_manifest_safety,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build research comparison analytics")
    parser.add_argument(
        "--bundle", action="append", required=True,
        help="label=/path/to/bundle (repeat for multiple bundles)",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--strict", action="store_true", help="Strict mode")
    parser.add_argument("--release-hold", default="HOLD", help="Expected release_hold value")
    args = parser.parse_args()

    # Parse bundles
    bundles = []
    for b in args.bundle:
        if "=" not in b:
            print(f"FAIL: invalid bundle format: {b} (expected label=/path)", file=sys.stderr)
            return 2
        label, path_str = b.split("=", 1)
        bundles.append((label, Path(path_str)))

    if len(bundles) < 2:
        print(f"FAIL: need at least 2 bundles, got {len(bundles)}", file=sys.stderr)
        return 2

    if args.release_hold != "HOLD":
        print(f"FAIL: release_hold must be HOLD, got {args.release_hold}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Program A: Bundle Series Loader ---
    try:
        records = load_bundle_series(bundles, strict=args.strict, release_hold=args.release_hold)
    except ValueError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2

    series_index = build_bundle_series_index(records)
    _write_json(output_dir, "bundle_series_index.json", series_index)

    if not series_index["all_safety_valid"]:
        print("FAIL: safety validation failed", file=sys.stderr)
        return 2

    if not series_index["all_json_parse_ok"]:
        print("FAIL: JSON parse errors", file=sys.stderr)
        return 2

    # --- Program B: Metric Extraction ---
    metrics = extract_metrics_from_records(records)
    metrics_json = build_extracted_metrics_json(metrics)
    _write_json(output_dir, "extracted_metrics.json", metrics_json)

    # --- Program C: Pairwise Comparison ---
    comparisons = compare_all_pairs(metrics, records)
    pairwise_json = build_pairwise_comparison_json(comparisons)
    _write_json(output_dir, "pairwise_comparison.json", pairwise_json)

    # --- Program D: Trend Engine (if 3+ bundles) ---
    if len(metrics) >= 3:
        trend_report = compute_trend_report(metrics)
        trend_json = trend_report_to_dict(trend_report)
    else:
        trend_json = {
            "schema_version": "1.0.0",
            "generated_at": "deterministic",
            "bundle_count": len(metrics),
            "labels": [m.label for m in metrics],
            "metric_trends": [],
            "detections": [],
            "overall_trend": "insufficient_data",
        }
    _write_json(output_dir, "trend_report.json", trend_json)

    # --- Program E: Regression Detector ---
    regression_reports = []
    for i in range(len(metrics)):
        for j in range(i + 1, len(metrics)):
            rr = detect_regressions(metrics[i], metrics[j])
            regression_reports.append({
                "left": metrics[i].label,
                "right": metrics[j].label,
                "report": regression_report_to_dict(rr),
            })

    regression_json = {
        "schema_version": "1.0.0",
        "generated_at": "deterministic",
        "pair_count": len(regression_reports),
        "pairs": regression_reports,
        "has_any_safety_regression": any(
            p["report"]["safety_regressions_count"] > 0 for p in regression_reports
        ),
    }
    _write_json(output_dir, "regression_report.json", regression_json)

    # --- Program F: Scorecard ---
    scorecard = build_scorecard(metrics)
    scorecard_json = scorecard_to_dict(scorecard)
    _write_json(output_dir, "comparison_scorecard.json", scorecard_json)

    # --- Program G: Markdown Report ---
    md_report = render_comparison_markdown(
        scorecard_json, metrics_json, pairwise_json,
        trend_json, regression_json, {},
    )
    (output_dir / "research_comparison_report.md").write_text(md_report)

    # --- Program H: HTML Report ---
    html_report = render_comparison_html(
        scorecard_json, metrics_json, pairwise_json,
        trend_json, regression_json, {},
    )
    (output_dir / "research_comparison_report.html").write_text(html_report)

    # --- Program I: Comparison Manifest ---
    output_artifact_names = (
        "bundle_series_index.json",
        "extracted_metrics.json",
        "pairwise_comparison.json",
        "trend_report.json",
        "regression_report.json",
        "comparison_scorecard.json",
        "research_comparison_report.md",
        "research_comparison_report.html",
        "research_comparison_manifest.json",
    )

    bundle_hashes = compute_bundle_hashes(records)
    # Pre-write manifest placeholder to include in hash computation
    placeholder_manifest = build_comparison_manifest(
        bundle_labels=tuple(r.label for r in records),
        bundle_hashes=bundle_hashes,
        output_artifact_hashes={},
    )
    _write_json(output_dir, "research_comparison_manifest.json", placeholder_manifest)

    output_hashes = compute_output_artifact_hashes(output_dir, output_artifact_names)

    manifest = build_comparison_manifest(
        bundle_labels=tuple(r.label for r in records),
        bundle_hashes=bundle_hashes,
        output_artifact_hashes=output_hashes,
        strict_mode=args.strict,
    )
    _write_json(output_dir, "research_comparison_manifest.json", manifest)

    # Validate manifest safety
    valid, safety_errors = validate_manifest_safety(manifest)
    if not valid:
        print(f"FAIL: manifest safety errors: {safety_errors}", file=sys.stderr)
        return 2

    # --- Summary ---
    has_safety_regression = regression_json.get("has_any_safety_regression", False)
    has_regression = any(
        p["report"]["has_regressions"] for p in regression_reports
    )

    if has_safety_regression:
        overall = "FAIL"
    elif has_regression:
        overall = "PARTIAL"
    else:
        overall = "PASS"

    print(f"{overall}: bundles={len(records)} comparisons={len(comparisons)} "
          f"regressions={sum(1 for p in regression_reports if p['report']['has_regressions'])} "
          f"scorecard={scorecard.best_composite_score}")

    return 0 if overall == "PASS" else (1 if overall == "FAIL" else 0)


def _write_json(output_dir: Path, name: str, data: dict) -> None:
    """Write JSON artifact."""
    (output_dir / name).write_text(json.dumps(data, sort_keys=True, indent=2))


if __name__ == "__main__":
    sys.exit(main())
