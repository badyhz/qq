#!/usr/bin/env python3
"""T1845 - CLI to render frozen backlog review dashboard HTML.

Usage:
    python scripts/render_frozen_backlog_review_dashboard.py --output-html FILE [--mode summary|full]

Exit 0 on success.
"""
from __future__ import annotations

import argparse
import sys

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_dashboard_renderer import (
    render_dashboard_html,
    render_hold_banner_html,
    render_summary_cards_html,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render frozen backlog review dashboard HTML",
    )
    parser.add_argument(
        "--output-html",
        required=True,
        help="Output HTML file path",
    )
    parser.add_argument(
        "--mode",
        choices=("summary", "full"),
        default="full",
        help="Render mode: summary or full (default: full)",
    )
    args = parser.parse_args()

    summary, records = materialize_full_report(FROZEN_BACKLOG_INVENTORY)

    if args.mode == "summary":
        html_content = (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"UTF-8\">\n"
            "<title>Frozen Backlog Summary</title>\n"
            "<style>body{font-family:sans-serif;margin:20px;}"
            ".hold-banner{background:#d32f2f;color:#fff;padding:16px;"
            "border-radius:6px;margin-bottom:24px;font-size:18px;}"
            ".card-value{font-size:32px;font-weight:700;}"
            ".card-label{font-size:13px;color:#666;}"
            ".summary-cards{display:flex;gap:16px;}"
            ".card{background:#fff;padding:20px;border-radius:6px;"
            "box-shadow:0 1px 3px rgba(0,0,0,0.12);text-align:center;}"
            "</style>\n</head>\n<body>\n"
            "<h1>Frozen Backlog Summary</h1>\n"
            f"{render_hold_banner_html()}\n"
            f"{render_summary_cards_html(summary)}\n"
            "</body>\n</html>"
        )
    else:
        html_content = render_dashboard_html(summary, records)

    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Dashboard written to {args.output_html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
