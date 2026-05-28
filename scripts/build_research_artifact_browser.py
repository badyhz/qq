#!/usr/bin/env python3
"""Build research artifact browser — index, validate, render reports.

Usage:
    python3 scripts/build_research_artifact_browser.py \
        --quality-dir /tmp/multi_strategy_research_quality_gate \
        --output-dir /tmp/research_artifact_browser \
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

from core.research_artifact_browser import (
    artifact_browser_index_to_dict,
    build_artifact_browser_index,
    build_review_model,
    review_model_to_dict,
    validate_artifact_schema,
    schema_validation_to_dict,
)
from core.research_static_report_renderer import (
    render_html_report,
    render_human_review_checklist,
    render_human_review_checklist_markdown,
    render_markdown_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build research artifact browser")
    parser.add_argument("--quality-dir", required=True, help="Quality gate output directory")
    parser.add_argument("--output-dir", required=True, help="Browser output directory")
    parser.add_argument("--strict", action="store_true", help="Strict mode")
    parser.add_argument("--release-hold", default="HOLD", help="Expected release_hold value")
    args = parser.parse_args()

    quality_dir = Path(args.quality_dir)
    output_dir = Path(args.output_dir)

    if not quality_dir.exists():
        print(f"FAIL: quality directory missing: {quality_dir}", file=sys.stderr)
        return 2

    if args.release_hold != "HOLD":
        print(f"FAIL: release_hold must be HOLD, got {args.release_hold}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = "deterministic"

    # --- Program A: Artifact Indexer ---
    index = build_artifact_browser_index(quality_dir, generated_at=generated_at)
    index_dict = artifact_browser_index_to_dict(index)
    _write_json(output_dir, "artifact_browser_index.json", index_dict)

    if index.status == "FAIL":
        print(f"FAIL: {index.required_missing} required artifacts missing", file=sys.stderr)
        # Continue to generate remaining artifacts with FAIL status

    # --- Program B: Schema Validator ---
    schema_result = validate_artifact_schema(quality_dir, expected_release_hold=args.release_hold)
    schema_dict = schema_validation_to_dict(schema_result)
    _write_json(output_dir, "artifact_schema_validation.json", schema_dict)

    if schema_result.status == "FAIL":
        print(f"FAIL: schema validation errors: {len(schema_result.errors)}", file=sys.stderr)

    # --- Program C: Review View Model ---
    review = build_review_model(quality_dir)
    review_dict = review_model_to_dict(review)
    _write_json(output_dir, "review_model.json", review_dict)

    # --- Program D: HTML Renderer ---
    html_report = render_html_report(review_dict, index_dict, schema_dict, generated_at=generated_at)
    (output_dir / "artifact_browser.html").write_text(html_report)

    # --- Program E: Markdown Renderer ---
    md_report = render_markdown_report(review_dict, index_dict, schema_dict, generated_at=generated_at)
    (output_dir / "artifact_browser.md").write_text(md_report)

    # --- Program G: Human Review Checklist ---
    checklist = render_human_review_checklist(review_dict, generated_at=generated_at)
    _write_json(output_dir, "human_review_checklist.json", checklist)
    checklist_md = render_human_review_checklist_markdown(review_dict, generated_at=generated_at)
    (output_dir / "human_review_checklist.md").write_text(checklist_md)

    # --- Browser manifest ---
    browser_manifest = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "strict_mode": args.strict,
        "quality_dir": str(quality_dir),
        "index_status": index.status,
        "schema_status": schema_result.status,
        "verdict": review.verdict,
        "composite_score": review.composite_score,
        "artifacts": [
            "artifact_browser_index.json",
            "artifact_schema_validation.json",
            "review_model.json",
            "artifact_browser.html",
            "artifact_browser.md",
            "human_review_checklist.json",
            "human_review_checklist.md",
            "artifact_browser_manifest.json",
        ],
    }
    _write_json(output_dir, "artifact_browser_manifest.json", browser_manifest)

    # --- Summary ---
    overall = "PASS"
    if index.status == "FAIL" or schema_result.status == "FAIL":
        overall = "FAIL"
    elif review.verdict != "PASS":
        overall = "PARTIAL"

    print(f"{overall}: index={index.status} schema={schema_result.status} "
          f"verdict={review.verdict} score={review.composite_score:.4f}")

    return 0 if overall == "PASS" else (1 if overall == "FAIL" else 0)


def _write_json(output_dir: Path, name: str, data: dict) -> None:
    """Write JSON artifact."""
    (output_dir / name).write_text(json.dumps(data, sort_keys=True, indent=2))


if __name__ == "__main__":
    sys.exit(main())
