"""Phase 10D enabled strategies runner — runs all enabled strategies from config.

Default: offline sample, no real HTTP, no Feishu send, no secrets, no orders.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.strategy_config import load_strategy_config, StrategyLibrary
from core.paper_trading.strategy_registry import SignalCandidate
from core.paper_trading.strategy_switchboard import (
    build_jobs, run_switchboard, run_switchboard_offline, SwitchboardResult,
)
from core.paper_trading.data_source import DataSourceConfig
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.paper_trading.feishu_paper_alert_payload import build_payloads_from_preview

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")
DEFAULT_CONFIG = os.path.join(REPO_ROOT, "config", "strategies.yaml")

SAFETY_FLAGS = [
    "PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "STRATEGY_RUNNER_DRY_RUN_ONLY",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _candidate_to_plan(c: SignalCandidate) -> dict:
    """Convert SignalCandidate to plan dict for payload generation."""
    return {
        "symbol": c.symbol,
        "timeframe": c.timeframe,
        "direction": c.direction,
        "source_status": c.watch_state,
        "last_close": c.last_close,
        "entry_observation": c.entry_observation,
        "invalidation_level": c.invalidation_level,
        "take_profit_observation": c.take_profit_observation,
        "rr_ratio": c.rr_ratio,
        "risk_distance_pct": c.risk_distance_pct,
        "reward_distance_pct": c.reward_distance_pct,
        "plan_decision": "WATCH" if c.priority in ("HIGH", "MEDIUM") else "WAIT",
        "reason": f"{c.strategy_type}: {c.macd_state}, {c.watch_state}",
    }


def _write_reports(date_str: str, result: SwitchboardResult, library: StrategyLibrary):
    """Write strategy run reports."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Count by direction and priority
    long_count = sum(1 for c in result.candidates if c.direction == "LONG_OBSERVE")
    short_count = sum(1 for c in result.candidates if c.direction == "SHORT_OBSERVE")
    high_count = sum(1 for c in result.candidates if c.priority == "HIGH")
    medium_count = sum(1 for c in result.candidates if c.priority == "MEDIUM")
    low_count = sum(1 for c in result.candidates if c.priority == "LOW")

    # Group by strategy
    by_strategy: dict[str, list[SignalCandidate]] = {}
    for c in result.candidates:
        by_strategy.setdefault(c.strategy_id, []).append(c)

    # Build payload input (only WATCH candidates)
    watch_candidates = [c for c in result.candidates if c.priority in ("HIGH", "MEDIUM")]
    plans = [_candidate_to_plan(c) for c in watch_candidates]
    payload_input = {
        "date": date_str,
        "mode": result.mode,
        "plans": plans,
        "decision_counts": {
            "WATCH": len(plans),
            "WAIT": 0,
            "AVOID": 0,
        },
    }

    # JSON summary
    summary_data = {
        "date": date_str,
        "mode": result.mode,
        "total_jobs": result.total_jobs,
        "success_count": result.success_count,
        "fail_count": result.fail_count,
        "candidate_count": result.candidate_count,
        "enabled_strategies": result.enabled_strategies,
        "disabled_strategies": result.disabled_strategies,
        "direction_counts": {"LONG_OBSERVE": long_count, "SHORT_OBSERVE": short_count},
        "priority_counts": {"HIGH": high_count, "MEDIUM": medium_count, "LOW": low_count},
        "by_strategy": {k: len(v) for k, v in by_strategy.items()},
        "errors": result.errors,
        "safety_flags": SAFETY_FLAGS,
        "send_attempted": False,
        "actually_sent": False,
    }

    json_path = os.path.join(REPORT_DIR, f"{date_str}_strategy_run_summary.json")
    with open(json_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nJSON: {json_path}")

    # Payload input
    payload_path = os.path.join(REPORT_DIR, f"{date_str}_strategy_payload_input.json")
    with open(payload_path, "w") as f:
        json.dump(payload_input, f, indent=2)
    print(f"Payload input: {payload_path}")

    # CSV candidates
    csv_path = os.path.join(REPORT_DIR, f"{date_str}_strategy_candidates.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy_id", "strategy_type", "symbol", "timeframe",
                         "watch_state", "direction", "priority", "last_close",
                         "entry_observation", "invalidation_level", "rr_ratio"])
        for c in result.candidates:
            writer.writerow([c.strategy_id, c.strategy_type, c.symbol, c.timeframe,
                             c.watch_state, c.direction, c.priority, c.last_close,
                             c.entry_observation, c.invalidation_level, c.rr_ratio])
    print(f"CSV: {csv_path}")

    # Markdown
    md_path = os.path.join(REPORT_DIR, f"{date_str}_strategy_run_summary.md")
    with open(md_path, "w") as f:
        f.write(f"# 策略运行摘要 — {date_str}\n\n")
        f.write(f"## 摘要\n\n")
        f.write(f"- **模式:** {result.mode}\n")
        f.write(f"- **总任务:** {result.total_jobs}\n")
        f.write(f"- **成功:** {result.success_count}\n")
        f.write(f"- **失败:** {result.fail_count}\n")
        f.write(f"- **候选信号:** {result.candidate_count}\n")
        f.write(f"- **发送尝试:** 否\n")
        f.write(f"- **实际发送:** 否\n\n")

        f.write(f"## 启用策略\n\n")
        for sid in result.enabled_strategies:
            strat = library.strategies[sid]
            f.write(f"- **{sid}:** {strat.description}\n")
            f.write(f"  - 类型: {strat.strategy_type}\n")
            f.write(f"  - 币种: {', '.join(strat.symbols)}\n")
            f.write(f"  - 周期: {', '.join(strat.timeframes)}\n")

        if result.disabled_strategies:
            f.write(f"\n## 关闭策略\n\n")
            for sid in result.disabled_strategies:
                strat = library.strategies[sid]
                f.write(f"- **{sid}:** {strat.description} (已关闭)\n")

        f.write(f"\n## 信号统计\n\n")
        f.write(f"| 方向 | 数量 |\n|---|---|\n")
        f.write(f"| 多头观察 | {long_count} |\n")
        f.write(f"| 空头观察 | {short_count} |\n")

        f.write(f"\n| 优先级 | 数量 |\n|---|---|\n")
        f.write(f"| HIGH | {high_count} |\n")
        f.write(f"| MEDIUM | {medium_count} |\n")
        f.write(f"| LOW | {low_count} |\n")

        if by_strategy:
            f.write(f"\n## 按策略分组\n\n")
            for sid, cands in by_strategy.items():
                f.write(f"### {sid}\n\n")
                for c in cands:
                    f.write(f"- {c.symbol} {c.timeframe}: {c.watch_state} ({c.direction})\n")

        if result.errors:
            f.write(f"\n## 错误\n\n")
            for err in result.errors:
                f.write(f"- {err['job']}: {err['error']}\n")

        f.write(f"\n## 安全边界\n\n")
        f.write("- 纸面观察，不下单\n")
        f.write("- 只读行情数据\n")
        f.write("- 不涉及账户、订单、testnet、live\n")
        f.write("- 不读取 websocket、secret、.env\n")
        f.write("- 不真实发送飞书\n")
    print(f"Markdown: {md_path}")


def run_offline(config_path: str, date_str: str) -> int:
    """Run strategies in offline mode."""
    print(f"=== Phase 10D Enabled Strategies Runner (offline) ===\n")
    library = load_strategy_config(config_path)

    print(f"Config: {config_path}")
    print(f"Enabled: {list(library.enabled_strategies.keys())}")
    print(f"Disabled: {list(library.disabled_strategies.keys())}")

    result = run_switchboard_offline(library, date_str)
    _write_reports(date_str, result, library)

    print(f"\n=== Offline Complete ===")
    print(f"Candidates: {result.candidate_count}")
    return 0


def run_real_http(config_path: str, date_str: str, limit: int = 120) -> int:
    """Run strategies with real public HTTP data."""
    print(f"=== Phase 10D Enabled Strategies Runner (real HTTP) ===\n")
    library = load_strategy_config(config_path)

    print(f"Config: {config_path}")
    print(f"Enabled: {list(library.enabled_strategies.keys())}")
    print(f"Disabled: {list(library.disabled_strategies.keys())}")

    config = DataSourceConfig(mode="snapshot", network_enabled=True)
    adapter = BinancePublicKlineAdapter(config)

    result = run_switchboard(library, adapter, date_str, mode="real_public_http", limit=limit)
    _write_reports(date_str, result, library)

    print(f"\n=== Real HTTP Complete ===")
    print(f"Candidates: {result.candidate_count}")
    print(f"Errors: {len(result.errors)}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 10D enabled strategies runner")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG)
    parser.add_argument("--allow-public-http", action="store_true")
    parser.add_argument("--offline-sample", action="store_true")
    parser.add_argument("--strategy", type=str, action="append", default=None)
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()

    date_str = args.date or _today_str()

    # Default to offline if neither specified
    if not args.allow_public_http and not args.offline_sample:
        args.offline_sample = True

    if args.offline_sample:
        return run_offline(args.config, date_str)
    else:
        return run_real_http(args.config, date_str, args.limit)


if __name__ == "__main__":
    sys.exit(main())
