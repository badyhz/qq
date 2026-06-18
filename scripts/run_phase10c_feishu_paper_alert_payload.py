"""Phase 10C-3J runner: build Feishu-ready paper alert payload files.

Dry-run artifact generation only. This script does not send webhooks.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.feishu_paper_alert_payload import (  # noqa: E402
    build_payloads_from_preview,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "phase10c" / "emergency"
DEFAULT_DATE = "2026-06-18"
DEFAULT_INPUT = REPORT_DIR / f"{DEFAULT_DATE}_focused_paper_plan_preview.json"
DEFAULT_JSON_OUT = REPORT_DIR / f"{DEFAULT_DATE}_feishu_paper_alert_payload.json"
DEFAULT_MD_OUT = REPORT_DIR / f"{DEFAULT_DATE}_feishu_paper_alert_payload.md"


def run(input_path: Path, json_out: Path, md_out: Path) -> dict:
    preview = json.loads(input_path.read_text(encoding="utf-8"))
    payload_file = build_payloads_from_preview(preview)

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload_file, indent=2), encoding="utf-8")
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(render_markdown(payload_file), encoding="utf-8")
    return payload_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 10C-3J Feishu-ready paper alert payload")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"ERROR: input not found: {args.input}")
        return 1

    payload_file = run(args.input, args.output_json, args.output_md)
    print(
        "payload_count={count} dry_run_only={dry} webhook_send_attempted={sent} verdict={verdict}".format(
            count=payload_file["payload_count"],
            dry=payload_file["dry_run_only"],
            sent=payload_file["webhook_send_attempted"],
            verdict=payload_file["final_verdict"],
        )
    )
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
