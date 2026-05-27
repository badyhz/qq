#!/usr/bin/env python3
"""CLI: Build offline shadow research bundle from component files.

Reads plan.json, matrix.json, results.json, scorecard.json from an
input directory, renders reports, and writes all artifacts + manifest
to an output directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_shadow_bundle_builder import build_bundle
from core.offline_shadow_report_renderer import (
    render_report_html,
    render_report_json,
    render_report_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build offline shadow research bundle"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing plan.json, matrix.json, results.json, scorecard.json",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write bundle artifacts",
    )
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    # Load inputs
    required_files = ["plan.json", "matrix.json", "results.json", "scorecard.json"]
    for name in required_files:
        path = input_dir / name
        if not path.exists():
            print(f"ERROR: missing {path}", file=sys.stderr)
            return 1

    plan_data = json.loads((input_dir / "plan.json").read_text())
    matrix_data = json.loads((input_dir / "matrix.json").read_text())
    results_data = json.loads((input_dir / "results.json").read_text())
    scorecard_data = json.loads((input_dir / "scorecard.json").read_text())

    # Render reports
    report_md = render_report_markdown(results_data)
    report_html = render_report_html(results_data)
    report_json_data = render_report_json(results_data)

    # Build bundle
    bundle = build_bundle(
        plan_data=plan_data,
        matrix_data=matrix_data,
        results_data=results_data,
        scorecard_data=scorecard_data,
        report_markdown=report_md,
        report_html=report_html,
        report_json=report_json_data,
    )

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in bundle.items():
        (output_dir / name).write_text(content)

    # Verify manifest
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["release_hold"] == "HOLD"
    assert manifest["no_live"] is True
    assert manifest["no_submit"] is True
    assert manifest["no_exchange"] is True

    print(f"Bundle written to {output_dir}")
    print(f"  artifacts: {manifest['artifact_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
