"""Phase 10F Strategy → Trade Intent runner.

Reads strategy_payload_input.json, generates shadow-only TradeIntents.
No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.trade_intent import build_trade_intent, TradeIntent
from core.paper_trading.trade_intent_risk_gate import validate_trade_intent

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "TRADE_INTENT_DRY_RUN_ONLY",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_input_path(date_str: str) -> str:
    return os.path.join(REPORT_DIR, f"{date_str}_strategy_payload_input.json")


def run_intents(
    input_path: str,
    date_str: str,
    paper_equity: float = 10000.0,
    max_risk_pct: float = 0.5,
) -> dict:
    """Generate trade intents from strategy payload input."""
    with open(input_path) as f:
        payload_input = json.load(f)

    plans = [p for p in payload_input.get("plans", []) if isinstance(p, dict)]
    intents: list[dict] = []
    shadow_count = 0
    blocked_count = 0
    invalid_count = 0

    for plan in plans:
        intent = build_trade_intent(plan, date_str, paper_equity, max_risk_pct)
        intent_dict = intent.to_dict()

        # Run risk gate
        gate = validate_trade_intent(intent_dict)
        intent_dict["risk_gate_status"] = gate.status
        intent_dict["risk_gate_reasons"] = gate.reasons
        intent_dict["intent_status"] = gate.status if gate.status != "PASS" else "SHADOW_READY"

        intents.append(intent_dict)

        if intent_dict["intent_status"] == "SHADOW_READY":
            shadow_count += 1
        elif intent_dict["intent_status"] == "BLOCKED_BY_RISK_GATE":
            blocked_count += 1
        else:
            invalid_count += 1

    result = {
        "date": date_str,
        "source": "strategy_runner",
        "source_mode": payload_input.get("mode", "unknown"),
        "intent_count": len(intents),
        "status_counts": {
            "SHADOW_READY": shadow_count,
            "BLOCKED_BY_RISK_GATE": blocked_count,
            "INVALID": invalid_count,
        },
        "intents": intents,
        "paper_equity_preview": paper_equity,
        "max_risk_pct": max_risk_pct,
        "dry_run_only": True,
        "actually_executed": False,
        "order_attempted": False,
        "safety_flags": SAFETY_FLAGS,
    }
    return result


def render_markdown(result: dict) -> str:
    """Render human-readable markdown from trade intent result."""
    counts = result.get("status_counts", {})
    lines = [
        "# Strategy Trade Intent Preview",
        "",
        f"**Date:** {result.get('date', '')}",
        f"**Source:** {result.get('source', '')}",
        f"**Mode:** {result.get('source_mode', '')}",
        f"**Paper equity:** {result.get('paper_equity_preview', 0)}",
        f"**Max risk %:** {result.get('max_risk_pct', 0)}%",
        "",
        "## Summary",
        "",
        f"- SHADOW_READY: {counts.get('SHADOW_READY', 0)}",
        f"- BLOCKED_BY_RISK_GATE: {counts.get('BLOCKED_BY_RISK_GATE', 0)}",
        f"- INVALID: {counts.get('INVALID', 0)}",
        "",
        "自动交易意图预览",
        "",
        "状态：shadow-only",
        "不会下单",
        "不会连接账户",
        "不会 testnet/live",
        "",
        f"本次生成：",
        f"- SHADOW_READY: {counts.get('SHADOW_READY', 0)}",
        f"- BLOCKED_BY_RISK_GATE: {counts.get('BLOCKED_BY_RISK_GATE', 0)}",
        f"- INVALID: {counts.get('INVALID', 0)}",
        "",
    ]

    intents = result.get("intents", [])

    # SHADOW_READY
    shadow = [i for i in intents if i.get("intent_status") == "SHADOW_READY"]
    if shadow:
        lines.append("## SHADOW_READY")
        lines.append("")
        for i in shadow:
            lines.extend(_intent_lines(i))
            lines.append("")

    # BLOCKED
    blocked = [i for i in intents if i.get("intent_status") == "BLOCKED_BY_RISK_GATE"]
    if blocked:
        lines.append("## BLOCKED_BY_RISK_GATE")
        lines.append("")
        for i in blocked:
            lines.extend(_intent_lines(i))
            lines.append("")

    # INVALID
    invalid = [i for i in intents if i.get("intent_status") == "INVALID"]
    if invalid:
        lines.append("## INVALID")
        lines.append("")
        for i in invalid:
            lines.extend(_intent_lines(i))
            lines.append("")

    # Risk Gate summary
    lines.extend([
        "## Risk Gate",
        "",
        "- rr_ratio >= 1.5",
        "- risk_distance 0-5%",
        "- reward > risk",
        "- max_risk_pct <= 0.5%",
        "- LONG: SL < entry, TP > entry",
        "- SHORT: SL > entry, TP < entry",
        "- execution_mode == shadow_only",
        "",
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


def _intent_lines(i: dict) -> list[str]:
    return [
        f"### {i.get('strategy_id', '')}｜{i.get('symbol', '')}｜{i.get('timeframe', '')}｜{i.get('side', '')}",
        "",
        f"- 策略：{i.get('strategy_id', '')}",
        f"- 标的：{i.get('symbol', '')}",
        f"- 周期：{i.get('timeframe', '')}",
        f"- 方向：{i.get('side', '')}",
        f"- 观察入场价：{i.get('entry_price', 0)}",
        f"- 止损：{i.get('stop_loss', 0)}",
        f"- 止盈：{i.get('take_profit', 0)}",
        f"- R:R：{i.get('rr_ratio', 0)}",
        f"- 单笔最大风险：{i.get('max_risk_pct', 0)}%",
        f"- 纸面仓位预览：{round(i.get('position_size_preview', 0), 4)}",
        f"- 风控状态：{i.get('risk_gate_status', '')}",
        f"- 处理：shadow-only 记录，不下单",
    ]


def main():
    parser = argparse.ArgumentParser(description="Phase 10F strategy trade intent runner")
    parser.add_argument("--input-file", type=str, default=None)
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=REPORT_DIR)
    parser.add_argument("--min-priority", type=str, default="LOW",
                        choices=["LOW", "MEDIUM", "HIGH"])
    parser.add_argument("--strategy", type=str, default=None)
    parser.add_argument("--paper-equity-preview", type=float, default=10000.0)
    parser.add_argument("--max-risk-pct", type=float, default=0.5)
    args = parser.parse_args()

    date_str = args.date or _today_str()
    input_path = args.input_file or _default_input_path(date_str)

    if not os.path.isfile(input_path):
        print(f"ERROR: input file not found: {input_path}")
        return 1

    result = run_intents(input_path, date_str, args.paper_equity_preview, args.max_risk_pct)

    # Filter by strategy if specified
    if args.strategy:
        result["intents"] = [i for i in result["intents"]
                             if i.get("strategy_id") == args.strategy]

    os.makedirs(args.output_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(args.output_dir, f"{date_str}_trade_intents.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"JSON: {json_path}")

    # Markdown
    md_path = os.path.join(args.output_dir, f"{date_str}_trade_intents.md")
    with open(md_path, "w") as f:
        f.write(render_markdown(result))
    print(f"Markdown: {md_path}")

    # Ledger JSONL
    ledger_path = os.path.join(args.output_dir, f"{date_str}_trade_intent_ledger.jsonl")
    with open(ledger_path, "w") as f:
        for intent in result["intents"]:
            f.write(json.dumps(intent) + "\n")
    print(f"Ledger: {ledger_path}")

    counts = result["status_counts"]
    print(f"\n=== Trade Intent Complete ===")
    print(f"Total: {result['intent_count']}")
    print(f"SHADOW_READY: {counts['SHADOW_READY']}")
    print(f"BLOCKED: {counts['BLOCKED_BY_RISK_GATE']}")
    print(f"INVALID: {counts['INVALID']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
