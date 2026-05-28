#!/usr/bin/env python3
"""Render research human review report — re-render md/html from existing artifacts.

Usage:
    python3 scripts/render_research_human_review_report.py \
        --review-dir /tmp/research_human_review_packet \
        --output-dir /tmp/research_human_review_rendered

Safety: offline only. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_review_report import (
    render_review_html,
    render_review_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render research human review report")
    parser.add_argument("--review-dir", required=True, help="Review packet directory")
    parser.add_argument("--output-dir", required=True, help="Output directory for rendered reports")
    args = parser.parse_args()

    review_dir = Path(args.review_dir)
    if not review_dir.exists():
        print(f"FAIL: review directory not found: {review_dir}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load required artifacts
    required_files = {
        "review_packet.json": None,
        "review_checklist.json": None,
        "review_signoff_template.json": None,
        "blocker_resolution_ledger.json": None,
        "review_audit_trail.json": None,
    }

    for name in required_files:
        path = review_dir / name
        if not path.exists():
            print(f"FAIL: missing required artifact: {name}", file=sys.stderr)
            return 2
        try:
            required_files[name] = json.loads(path.read_text())
        except (json.JSONDecodeError, ValueError) as e:
            print(f"FAIL: corrupted JSON {name}: {e}", file=sys.stderr)
            return 2

    packet = required_files["review_packet.json"]
    checklist = required_files["review_checklist.json"]
    signoff_template = required_files["review_signoff_template.json"]
    blocker_ledger = required_files["blocker_resolution_ledger.json"]
    audit_trail = required_files["review_audit_trail.json"]

    # Render reports
    md_report = render_review_markdown(packet, checklist, signoff_template, blocker_ledger, audit_trail)
    (output_dir / "human_review_report.md").write_text(md_report)

    html_report = render_review_html(packet, checklist, signoff_template, blocker_ledger, audit_trail)
    (output_dir / "human_review_report.html").write_text(html_report)

    print(f"PASS: rendered reports to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
