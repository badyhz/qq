#!/usr/bin/env python3
"""Render frozen file disposition report.

Reads human_review_queue.json + archive_delete_decision_prep.json.
Produces JSON, markdown, and standalone offline HTML.

Usage:
    PYTHONPATH=. python3 scripts/render_frozen_file_disposition_report.py \
        --human-review-queue-dir /tmp/frozen_human_review_queue \
        --decision-prep-dir /tmp/frozen_archive_delete_decision_prep \
        --output-dir /tmp/frozen_file_disposition_report \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from core.frozen_file_disposition_report import (
    RELEASE_HOLD_REQUIRED,
    build_report,
    render_html,
    render_markdown,
    write_html,
    write_json,
    write_manifest,
    write_markdown,
    _load_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render frozen file disposition report")
    parser.add_argument("--human-review-queue-dir", required=True)
    parser.add_argument("--decision-prep-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_file_disposition_report")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    queue_path = pathlib.Path(args.human_review_queue_dir) / "human_review_queue.json"
    prep_path = pathlib.Path(args.decision_prep_dir) / "archive_delete_decision_prep.json"

    if not queue_path.exists():
        print(f"FAIL: {queue_path} not found.", file=sys.stderr)
        return 1
    if not prep_path.exists():
        print(f"FAIL: {prep_path} not found.", file=sys.stderr)
        return 1

    queue_items = _load_json(queue_path)
    prep_items = _load_json(prep_path)

    report = build_report(queue_items, prep_items, release_hold=args.release_hold)
    md = render_markdown(report)
    html = render_html(report)

    out_dir = pathlib.Path(args.output_dir)
    write_json(report, out_dir / "frozen_file_disposition_report.json")
    write_manifest(report, out_dir / "frozen_file_disposition_manifest.json")
    write_markdown(md, out_dir / "frozen_file_disposition_report.md")
    write_html(html, out_dir / "frozen_file_disposition_report.html")

    print(f"OK: disposition report rendered for {report['frozen_file_count']} files")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
