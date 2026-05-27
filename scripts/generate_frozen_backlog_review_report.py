#!/usr/bin/env python3
"""T1532 - Frozen Backlog Review Report CLI.

Generates markdown and JSON reports from the frozen backlog inventory.
Pure deterministic. No network. No live calls.
Exit 0 on success, 1 on error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path so core/ imports work
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_json import render_report_json, render_summary_dict
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_report_renderer import render_report_markdown, render_summary_markdown


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate frozen backlog review report."
    )
    parser.add_argument(
        "--output-md",
        type=str,
        default=None,
        help="Path to write markdown report.",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Path to write JSON report.",
    )
    parser.add_argument(
        "--mode",
        choices=("summary", "full"),
        default="summary",
        help="Report mode: summary (default) or full.",
    )
    return parser.parse_args(argv)


def _write_file(path_str: str, content: str) -> None:
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.output_md and not args.output_json:
        print("ERROR: at least one of --output-md or --output-json is required.", file=sys.stderr)
        return 1

    inventory = FROZEN_BACKLOG_INVENTORY
    summary, records = materialize_full_report(inventory)

    # --- Markdown ---
    if args.output_md:
        if args.mode == "full":
            md_content = render_report_markdown(summary, records)
        else:
            md_content = render_summary_markdown(summary)
        _write_file(args.output_md, md_content)
        print(f"Markdown report written to {args.output_md}")

    # --- JSON ---
    if args.output_json:
        if args.mode == "full":
            json_content = render_report_json(summary, records)
        else:
            json_content = json.dumps(
                {"summary": render_summary_dict(summary)},
                sort_keys=True,
                indent=2,
            )
        _write_file(args.output_json, json_content)
        print(f"JSON report written to {args.output_json}")

    print(f"Mode: {args.mode} | Files: {inventory.total_count} | HOLD: active")
    return 0


if __name__ == "__main__":
    sys.exit(main())
