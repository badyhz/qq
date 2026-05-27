#!/usr/bin/env python3
"""Build multi-strategy research bundle — gather artifacts, build index, manifest, reports.

Usage:
    python3 scripts/build_multi_strategy_research_bundle.py \
        --input-dir /tmp/multi_strategy_research_workbench \
        --output-dir /tmp/multi_strategy_research_workbench

Output: artifact_index.json, report.md, report.html, manifest.json

Safety: local only, no network, no exchange.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_artifact_index import artifact_index_to_json, build_artifact_index
from core.research_workbench_manifest import build_manifest, manifest_to_json
from core.research_workbench_report import render_html_report, render_markdown_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build research bundle")
    parser.add_argument("--input-dir", required=True, help="Input directory with artifacts")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build artifact index
    index = build_artifact_index(input_dir)
    index_path = output_dir / "artifact_index.json"
    index_path.write_text(artifact_index_to_json(index))
    print(f"Wrote {index_path}")

    # Build manifest
    manifest = build_manifest(input_dir)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(manifest_to_json(manifest))
    print(f"Wrote {manifest_path}")

    # Build reports from available data
    report_data: dict = {"manifest": {"release_hold": "HOLD", "no_live": True, "no_submit": True, "no_exchange": True, "no_network": True}}

    # Load available artifacts for report
    for name in ["strategy_registry.json", "parameter_search.json", "results.json", "portfolio_summary.json", "comparison.json"]:
        path = input_dir / name
        if path.exists():
            key = name.replace(".json", "")
            report_data[key] = json.loads(path.read_text())

    # Load promotion recommendations
    promo_path = input_dir / "promotion_recommendations.json"
    if promo_path.exists():
        report_data["promotion_recommendations"] = json.loads(promo_path.read_text())

    # Load results summary
    results_path = input_dir / "results.json"
    if results_path.exists():
        rd = json.loads(results_path.read_text())
        report_data["results"] = rd
        report_data["strategy_count"] = len(set(r.get("strategy_id", "") for r in rd.get("results", [])))
        report_data["total_rows"] = rd.get("total_rows", 0)

    md = render_markdown_report(report_data)
    md_path = output_dir / "report.md"
    md_path.write_text(md)
    print(f"Wrote {md_path}")

    html = render_html_report(report_data)
    html_path = output_dir / "report.html"
    html_path.write_text(html)
    print(f"Wrote {html_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
