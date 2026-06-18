"""Phase 10E Strategy → Feishu payload bridge script.

Reads strategy_payload_input.json, generates Feishu payloads with Chinese labels.
No send, no secrets, no orders, no webhook.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.strategy_feishu_alert_bridge import (
    build_strategy_payloads, render_strategy_markdown,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "STRATEGY_PAYLOAD_DRY_RUN_ONLY",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_input_path(date_str: str) -> str:
    return os.path.join(REPORT_DIR, f"{date_str}_strategy_payload_input.json")


def main():
    parser = argparse.ArgumentParser(description="Phase 10E strategy Feishu payload bridge")
    parser.add_argument("--input", type=str, default=None,
                        help="Path to strategy_payload_input.json")
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    date_str = args.date or _today_str()
    input_path = args.input or _default_input_path(date_str)

    if not os.path.isfile(input_path):
        print(f"ERROR: input file not found: {input_path}")
        return 1

    with open(input_path) as f:
        payload_input = json.load(f)

    result = build_strategy_payloads(payload_input)

    os.makedirs(REPORT_DIR, exist_ok=True)

    # Write JSON
    json_path = os.path.join(REPORT_DIR, f"{date_str}_strategy_feishu_payload.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"JSON: {json_path}")

    # Write Markdown
    md_path = os.path.join(REPORT_DIR, f"{date_str}_strategy_feishu_payload.md")
    with open(md_path, "w") as f:
        f.write(render_strategy_markdown(result))
    print(f"Markdown: {md_path}")

    print(f"\n=== Strategy Feishu Payload Complete ===")
    print(f"Payloads: {result['payload_count']}")
    print(f"Dry-run only: {result['dry_run_only']}")
    print(f"Actually sent: {result['actually_sent']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
