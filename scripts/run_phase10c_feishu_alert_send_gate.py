"""Phase 10C-3K Feishu alert send gate — controlled send with dry-run default. No secrets, no auto-send."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.feishu_alert_send_gate import run_send_gate, SendResult, SEND_GATE_SAFETY_FLAGS

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "phase10c", "emergency")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _write_send_result(date_str: str, result: SendResult):
    """Write send result JSON and MD."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    # JSON
    json_path = os.path.join(REPORT_DIR, f"{date_str}_feishu_send_result.json")
    with open(json_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    print(f"\nJSON: {json_path}")

    # Markdown
    md_path = os.path.join(REPORT_DIR, f"{date_str}_feishu_send_result.md")
    with open(md_path, "w") as f:
        f.write(f"# Feishu Alert Send Result — {date_str}\n\n")
        f.write(f"## Send Gate Status\n\n")
        f.write(f"- **dry_run:** {result.dry_run}\n")
        f.write(f"- **allow_send:** {result.allow_send}\n")
        f.write(f"- **webhook_url_provided:** {result.webhook_url_provided}\n")
        f.write(f"- **send_attempted:** {result.send_attempted}\n")
        f.write(f"- **actually_sent:** {result.actually_sent}\n")
        f.write(f"- **payload_count:** {result.payload_count}\n")
        f.write(f"- **sent_count:** {result.sent_count}\n")
        f.write(f"- **failed_count:** {result.failed_count}\n")
        f.write(f"- **safety_passed:** {result.safety_passed}\n")

        if result.errors:
            f.write(f"\n## Errors\n\n")
            for err in result.errors:
                f.write(f"- {err}\n")

        f.write(f"\n## Safety Flags\n\n")
        for flag in result.safety_flags:
            f.write(f"- {flag}\n")

        f.write(f"\n## Safety\n\n")
        f.write("Send gate controls Feishu webhook delivery.\n")
        f.write("Default dry-run. Requires explicit --allow-send and --webhook-url.\n")
        f.write("No secrets read. No orders. Not testnet/live.\n")
    print(f"Markdown: {md_path}")


def main():
    parser = argparse.ArgumentParser(description="Phase 10C-3K Feishu alert send gate")
    parser.add_argument("--date", type=str, default=_today_str())
    parser.add_argument("--payload-file", type=str, default=None)
    parser.add_argument("--allow-send", action="store_true")
    parser.add_argument("--webhook-url", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    date_str = args.date

    # Default payload file
    if args.payload_file:
        payload_file = args.payload_file
    else:
        payload_file = os.path.join(REPORT_DIR, f"{date_str}_feishu_paper_alert_payload.json")

    print(f"=== Phase 10C-3K Feishu Alert Send Gate ===\n")
    print(f"Date: {date_str}")
    print(f"Payload file: {payload_file}")
    print(f"allow_send: {args.allow_send}")
    print(f"webhook_url_provided: {args.webhook_url is not None}")
    print(f"dry_run override: {args.dry_run}")
    print()

    # If --dry-run is explicitly set, force dry-run
    allow_send = args.allow_send and not args.dry_run
    webhook_url = args.webhook_url if allow_send else None

    result = run_send_gate(
        payload_file_path=payload_file,
        allow_send=allow_send,
        webhook_url=webhook_url,
    )

    _write_send_result(date_str, result)

    print(f"\n=== Send Gate Result ===")
    print(f"dry_run: {result.dry_run}")
    print(f"allow_send: {result.allow_send}")
    print(f"webhook_url_provided: {result.webhook_url_provided}")
    print(f"send_attempted: {result.send_attempted}")
    print(f"actually_sent: {result.actually_sent}")
    print(f"payload_count: {result.payload_count}")
    print(f"sent_count: {result.sent_count}")
    print(f"failed_count: {result.failed_count}")
    print(f"safety_passed: {result.safety_passed}")

    if result.errors:
        print(f"\nErrors:")
        for err in result.errors:
            print(f"  - {err}")

    print(f"\n=== Complete ===")
    return 0 if result.safety_passed else 1


if __name__ == "__main__":
    sys.exit(main())
