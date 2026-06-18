"""Phase 10G Paper Position Simulator runner.

Reads trade_intents.json, creates paper positions, optionally updates with klines.
No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.paper_position_simulator import (
    simulate_intent_only, simulate_with_klines,
)
from core.paper_trading.data_source import DataSourceConfig
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "POSITION_SIMULATOR_DRY_RUN_ONLY",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_input_path(date_str: str) -> str:
    return os.path.join(REPORT_DIR, f"{date_str}_trade_intents.json")


def render_markdown(result: dict) -> str:
    """Render human-readable markdown from simulation result."""
    counts = result.get("status_counts", {})
    lines = [
        "# Paper Position Simulator",
        "",
        f"**Date:** {result.get('date', '')}",
        f"**Mode:** {result.get('mode', '')}",
        f"**Positions:** {result.get('position_count', 0)}",
        "",
        "## Summary",
        "",
        f"- OPEN: {counts.get('OPEN', 0)}",
        f"- TAKE_PROFIT_HIT: {counts.get('TAKE_PROFIT_HIT', 0)}",
        f"- STOP_LOSS_HIT: {counts.get('STOP_LOSS_HIT', 0)}",
        f"- TIMEOUT_EXIT: {counts.get('TIMEOUT_EXIT', 0)}",
        f"- INVALID: {counts.get('INVALID', 0)}",
        "",
        "纸面持仓模拟",
        "",
        "状态：shadow-only",
        "不会下单",
        "不会连接账户",
        "不会 testnet/live",
        "",
        "本次生成：",
        f"- OPEN: {counts.get('OPEN', 0)}",
        f"- TAKE_PROFIT_HIT: {counts.get('TAKE_PROFIT_HIT', 0)}",
        f"- STOP_LOSS_HIT: {counts.get('STOP_LOSS_HIT', 0)}",
        f"- TIMEOUT_EXIT: {counts.get('TIMEOUT_EXIT', 0)}",
        "",
    ]

    positions = result.get("positions", [])

    # Group by status
    open_pos = [p for p in positions if p.get("status") == "OPEN"]
    tp_pos = [p for p in positions if p.get("status") == "TAKE_PROFIT_HIT"]
    sl_pos = [p for p in positions if p.get("status") == "STOP_LOSS_HIT"]
    timeout_pos = [p for p in positions if p.get("status") == "TIMEOUT_EXIT"]

    for label, group in [
        ("OPEN", open_pos), ("TAKE_PROFIT_HIT", tp_pos),
        ("STOP_LOSS_HIT", sl_pos), ("TIMEOUT_EXIT", timeout_pos),
    ]:
        if group:
            lines.append(f"## {label}")
            lines.append("")
            for p in group:
                lines.extend(_position_lines(p))
                lines.append("")

    # Strategy summary
    summary = result.get("summary", {})
    by_strat = summary.get("by_strategy", {})
    if by_strat:
        lines.extend(["## Strategy Summary", ""])
        for sid, stats in by_strat.items():
            lines.append(f"### {sid}")
            lines.append("")
            lines.append(f"- Total: {stats.get('total', 0)}")
            lines.append(f"- OPEN: {stats.get('OPEN', 0)}")
            lines.append(f"- TP: {stats.get('TAKE_PROFIT_HIT', 0)}")
            lines.append(f"- SL: {stats.get('STOP_LOSS_HIT', 0)}")
            lines.append(f"- Timeout: {stats.get('TIMEOUT_EXIT', 0)}")
            lines.append(f"- Realized PnL: {stats.get('total_realized_pnl', 0)}")
            lines.append(f"- Avg R: {stats.get('avg_r_multiple', 0)}")
            lines.append("")

    lines.extend([
        "## Safety",
        "",
        "- Paper-only: YES",
        "- Shadow-only: YES",
        "- No order: YES",
        "- No account: YES",
        "- No testnet/live: YES",
        "- No secret: YES",
        "- No real execution: YES",
        "",
    ])
    return "\n".join(lines)


def _position_lines(p: dict) -> list[str]:
    return [
        f"### {p.get('strategy_id', '')}｜{p.get('symbol', '')}｜{p.get('timeframe', '')}｜{p.get('side', '')}",
        "",
        f"- 策略：{p.get('strategy_id', '')}",
        f"- 标的：{p.get('symbol', '')}",
        f"- 周期：{p.get('timeframe', '')}",
        f"- 方向：{p.get('side', '')}",
        f"- 入场价：{p.get('entry_price', 0)}",
        f"- 止损：{p.get('stop_loss', 0)}",
        f"- 止盈：{p.get('take_profit', 0)}",
        f"- 状态：{p.get('status', '')}",
        f"- 纸面仓位：{round(p.get('position_size_preview', 0), 6)}",
        f"- 纸面盈亏：{round(p.get('realized_pnl', 0), 6)}",
        f"- R 倍数：{p.get('r_multiple', 0)}",
        f"- 处理：paper/shadow 记录，不下单",
    ]


def main():
    parser = argparse.ArgumentParser(description="Phase 10G paper position simulator")
    parser.add_argument("--input-file", type=str, default=None)
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=REPORT_DIR)
    parser.add_argument("--allow-public-http", action="store_true")
    parser.add_argument("--update-with-klines", action="store_true")
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--timeout-bars", type=int, default=24)
    parser.add_argument("--paper-equity-preview", type=float, default=10000.0)
    args = parser.parse_args()

    date_str = args.date or _today_str()
    input_path = args.input_file or _default_input_path(date_str)

    if not os.path.isfile(input_path):
        print(f"ERROR: input file not found: {input_path}")
        return 1

    with open(input_path) as f:
        intents_data = json.load(f)

    intents = intents_data.get("intents", [])
    shadow_intents = [i for i in intents if i.get("intent_status") == "SHADOW_READY"]
    print(f"Total intents: {len(intents)}")
    print(f"SHADOW_READY: {len(shadow_intents)}")

    if args.allow_public_http and args.update_with_klines:
        print("Mode: public_readonly_update")
        config = DataSourceConfig(mode="snapshot", network_enabled=True)
        adapter = BinancePublicKlineAdapter(config)

        # Fetch bars for each unique symbol/timeframe
        bars_by_key: dict = {}
        unique_keys: set = set()
        for intent in shadow_intents:
            sym = intent.get("symbol", "")
            tf = intent.get("timeframe", "")
            unique_keys.add(f"{sym}_{tf}")

        for key in unique_keys:
            sym, tf = key.rsplit("_", 1)
            print(f"  Fetching {sym} {tf}...", end=" ")
            try:
                bars = adapter.get_bars(sym, timeframe=tf, limit=args.limit)
                bars_by_key[key] = bars
                print(f"OK ({len(bars)} bars)")
            except Exception as e:
                print(f"ERROR: {e}")
            time.sleep(0.3)

        result = simulate_with_klines(
            shadow_intents, bars_by_key, date_str,
            paper_equity=args.paper_equity_preview,
            timeout_bars=args.timeout_bars,
        )
    else:
        print("Mode: intent_only")
        result = simulate_intent_only(
            shadow_intents, date_str,
            paper_equity=args.paper_equity_preview,
        )

    result_dict = result.to_dict()
    os.makedirs(args.output_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(args.output_dir, f"{date_str}_paper_positions.json")
    with open(json_path, "w") as f:
        json.dump(result_dict, f, indent=2)
    print(f"JSON: {json_path}")

    # Markdown
    md_path = os.path.join(args.output_dir, f"{date_str}_paper_positions.md")
    with open(md_path, "w") as f:
        f.write(render_markdown(result_dict))
    print(f"Markdown: {md_path}")

    # Ledger JSONL
    ledger_path = os.path.join(args.output_dir, f"{date_str}_paper_position_ledger.jsonl")
    with open(ledger_path, "w") as f:
        for pos in result_dict.get("positions", []):
            f.write(json.dumps(pos) + "\n")
    print(f"Ledger: {ledger_path}")

    # Summary
    summary_path = os.path.join(args.output_dir, f"{date_str}_paper_position_summary.json")
    with open(summary_path, "w") as f:
        json.dump({
            "date": date_str,
            "mode": result_dict["mode"],
            "status_counts": result_dict["status_counts"],
            "summary": result_dict["summary"],
            "safety_flags": SAFETY_FLAGS,
            "dry_run_only": True,
            "actually_executed": False,
        }, f, indent=2)
    print(f"Summary: {summary_path}")

    counts = result_dict["status_counts"]
    print(f"\n=== Paper Position Simulator Complete ===")
    print(f"Total: {result_dict['position_count']}")
    print(f"OPEN: {counts['OPEN']}")
    print(f"TP: {counts['TAKE_PROFIT_HIT']}")
    print(f"SL: {counts['STOP_LOSS_HIT']}")
    print(f"Timeout: {counts['TIMEOUT_EXIT']}")
    print(f"Invalid: {counts['INVALID']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
