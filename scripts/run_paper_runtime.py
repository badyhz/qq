"""Paper runtime CLI — one-command local paper trading run, no network."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.runtime_config import RuntimeConfig, load_config_from_json, default_config
from core.paper_trading.runtime_orchestrator import run_paper_runtime

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "paper_trading")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def find_fixtures() -> list:
    return sorted([
        os.path.join(FIXTURE_DIR, f)
        for f in os.listdir(FIXTURE_DIR)
        if f.endswith(".json") and f not in ("empty_sample.json", "malformed_sample.json")
    ])


def main():
    parser = argparse.ArgumentParser(description="Paper trading runtime")
    parser.add_argument("--config", help="Path to config JSON", default=None)
    args = parser.parse_args()

    print("=== Paper Trading Runtime ===\n")

    if args.config:
        config = load_config_from_json(args.config)
        print(f"Config: {args.config}")
    else:
        fixtures = find_fixtures()
        config = default_config(fixture_paths=fixtures)
        print("Config: default (all fixtures)")

    print(f"Strategy: {config.strategy_name}")
    print(f"Fixtures: {len(config.fixture_paths)}\n")

    result = run_paper_runtime(config)

    print(f"Status: {result.status}")
    print(f"Fixtures run: {result.fixtures_run}")
    print(f"Fixtures failed: {result.fixtures_failed}")
    print(f"Total signals: {result.total_signals}")
    print(f"Total plans: {result.total_plans}")
    print(f"Total rejected: {result.total_rejected}")
    print(f"Total trades: {result.total_trades}")
    print(f"Total PnL: {result.total_pnl}")
    print(f"Win rate: {result.win_rate:.2%}")
    print(f"Score: {result.score:.1f}")
    print(f"Rating: {result.rating}")
    print(f"Alerts: {result.alerts_written}")
    print()

    if result.alerts:
        print("=== Alerts ===")
        for a in result.alerts:
            print(f"  [{a.level.value}] {a.category}: {a.message}")
        print()

    # JSON output
    os.makedirs(REPORT_DIR, exist_ok=True)
    json_path = os.path.join(REPORT_DIR, "paper_trading_runtime_result.json")
    json_data = {
        "status": result.status,
        "strategy_name": result.strategy_name,
        "fixtures_run": result.fixtures_run,
        "fixtures_failed": result.fixtures_failed,
        "total_signals": result.total_signals,
        "total_plans": result.total_plans,
        "total_rejected": result.total_rejected,
        "total_trades": result.total_trades,
        "total_pnl": result.total_pnl,
        "win_rate": result.win_rate,
        "score": result.score,
        "rating": result.rating,
        "alerts_written": result.alerts_written,
        "safety_flags": result.safety_flags,
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"JSON: {json_path}")

    # Markdown output
    md_path = os.path.join(REPORT_DIR, "paper_trading_runtime_report.md")
    with open(md_path, "w") as f:
        f.write("# Paper Trading Runtime Report\n\n")
        f.write("**Date:** 2026-06-16\n")
        f.write(f"**Strategy:** {result.strategy_name}\n")
        f.write(f"**Mode:** paper-only / local / no network\n\n")
        f.write("## Results\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Status | {result.status} |\n")
        f.write(f"| Fixtures run | {result.fixtures_run} |\n")
        f.write(f"| Fixtures failed | {result.fixtures_failed} |\n")
        f.write(f"| Total signals | {result.total_signals} |\n")
        f.write(f"| Total plans | {result.total_plans} |\n")
        f.write(f"| Total rejected | {result.total_rejected} |\n")
        f.write(f"| Total trades | {result.total_trades} |\n")
        f.write(f"| Total PnL | {result.total_pnl} |\n")
        f.write(f"| Win rate | {result.win_rate:.2%} |\n")
        f.write(f"| Score | {result.score:.1f} |\n")
        f.write(f"| Rating | {result.rating} |\n")
        f.write(f"| Alerts | {result.alerts_written} |\n\n")
        if result.alerts:
            f.write("## Alerts\n\n")
            for a in result.alerts:
                f.write(f"- [{a.level.value}] {a.category}: {a.message}\n")
            f.write("\n")
        f.write("## Safety\n\n")
        for flag in result.safety_flags:
            f.write(f"- {flag}\n")
    print(f"Markdown: {md_path}")

    print(f"\nStatus: PAPER_RUNTIME_COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
