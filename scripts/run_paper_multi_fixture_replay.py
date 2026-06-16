"""Multi-fixture replay runner — runs all paper trading fixtures, local only."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.risk_sizing import RiskSizingConfig
from core.paper_trading.exit_rules import ExitRuleConfig
from core.paper_trading.replay_engine import (
    ReplayBar, ReplayConfig, load_bars_from_fixture, run_replay,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "paper_trading")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def macd_rebound_signal(bars, i):
    if i < 10:
        return None
    recent_high = max(b.high for b in bars[max(0, i - 10):i])
    current = bars[i].close
    drop_pct = (recent_high - current) / recent_high * 100
    if drop_pct >= 3.0 and bars[i].close > bars[i].open:
        return {
            "symbol": "BTCUSDT", "side": "BUY",
            "entry_price": current,
            "stop_loss": current * 0.98,
            "take_profit": current * 1.06,
            "invalidation_price": current * 0.97,
            "signal_source": "macd_rebound_multi",
        }
    return None


def run_fixture(fixture_path: str, config: ReplayConfig) -> dict:
    try:
        bars = load_bars_from_fixture(fixture_path)
        if not bars:
            return {"fixture": os.path.basename(fixture_path), "status": "EMPTY", "error": "no bars"}
        result = run_replay(bars, macd_rebound_signal, config)
        summary = result.ledger.summary()
        return {
            "fixture": os.path.basename(fixture_path),
            "status": "OK",
            "bars": result.bars_processed,
            "signals_generated": result.signals_generated,
            "plans_created": result.plans_created,
            "plans_rejected": result.plans_created - result.plans_approved,
            "plans_portfolio_rejected": result.plans_portfolio_rejected,
            "trades_executed": result.trades_executed,
            "winners": summary["winners"],
            "losers": summary["losers"],
            "total_pnl": round(summary["total_pnl"], 2),
            "win_rate": round(summary["win_rate"], 4),
            "max_drawdown": summary["max_drawdown"],
            "exit_reason_distribution": summary["exit_reasons"],
            "safety_flags": ["NO_REAL_ORDER", "NO_REAL_HTTP", "NO_SECRET_READ", "PAPER_ONLY"],
        }
    except Exception as e:
        return {
            "fixture": os.path.basename(fixture_path),
            "status": "ERROR",
            "error": str(e),
        }


def main():
    print("=== Paper Multi-Fixture Replay Runner ===\n")

    config = ReplayConfig(
        risk_config=RiskSizingConfig(
            max_risk_per_trade_pct=1.0,
            max_position_pct=10.0,
            min_rr_ratio=1.5,
            max_margin_cap=50000,
            equity=100000,
        ),
        exit_config=ExitRuleConfig(
            stop_loss_pct=2.0,
            take_profit_pct=6.0,
            trailing_stop_pct=1.5,
            time_stop_bars=50,
        ),
        auto_approve=True,
    )

    # Find all fixtures
    fixtures = sorted([
        os.path.join(FIXTURE_DIR, f)
        for f in os.listdir(FIXTURE_DIR)
        if f.endswith(".json")
    ])
    print(f"Found {len(fixtures)} fixtures\n")

    results = []
    for fixture_path in fixtures:
        name = os.path.basename(fixture_path)
        print(f"Running: {name} ...")
        result = run_fixture(fixture_path, config)
        results.append(result)
        status = result["status"]
        if status == "OK":
            print(f"  OK: {result['trades_executed']} trades, pnl={result['total_pnl']}")
        elif status == "EMPTY":
            print(f"  EMPTY: {result.get('error', '')}")
        else:
            print(f"  ERROR: {result.get('error', '')}")

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "OK")
    err_count = sum(1 for r in results if r["status"] == "ERROR")
    empty_count = sum(1 for r in results if r["status"] == "EMPTY")
    total_pnl = sum(r.get("total_pnl", 0) for r in results if r["status"] == "OK")
    total_trades = sum(r.get("trades_executed", 0) for r in results if r["status"] == "OK")

    print(f"\n=== Summary ===")
    print(f"Fixtures: {len(fixtures)} total, {ok_count} OK, {err_count} errors, {empty_count} empty")
    print(f"Total trades: {total_trades}")
    print(f"Total PnL: {total_pnl}")

    # JSON output
    os.makedirs(REPORT_DIR, exist_ok=True)
    json_path = os.path.join(REPORT_DIR, "paper_trading_multi_fixture_summary.json")
    with open(json_path, "w") as f:
        json.dump({
            "total_fixtures": len(fixtures),
            "ok_count": ok_count,
            "error_count": err_count,
            "empty_count": empty_count,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "results": results,
        }, f, indent=2)
    print(f"\nJSON summary: {json_path}")

    # Markdown report
    md_path = os.path.join(REPORT_DIR, "paper_trading_multi_fixture_report.md")
    with open(md_path, "w") as f:
        f.write("# Paper Trading Multi-Fixture Replay Report\n\n")
        f.write(f"**Date:** 2026-06-16\n")
        f.write(f"**Mode:** paper-only / local / no network\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Total fixtures | {len(fixtures)} |\n")
        f.write(f"| OK | {ok_count} |\n")
        f.write(f"| Errors | {err_count} |\n")
        f.write(f"| Empty | {empty_count} |\n")
        f.write(f"| Total trades | {total_trades} |\n")
        f.write(f"| Total PnL | {total_pnl} |\n\n")
        f.write("## Results\n\n")
        f.write("| Fixture | Status | Trades | PnL | Win Rate |\n")
        f.write("|---------|--------|--------|-----|----------|\n")
        for r in results:
            status = r["status"]
            trades = r.get("trades_executed", "-")
            pnl = r.get("total_pnl", "-")
            wr = r.get("win_rate", "-")
            f.write(f"| {r['fixture']} | {status} | {trades} | {pnl} | {wr} |\n")
        f.write("\n## Safety\n\n")
        f.write("- NO_REAL_ORDER\n")
        f.write("- NO_REAL_HTTP\n")
        f.write("- NO_SECRET_READ\n")
        f.write("- NO_TESTNET\n")
        f.write("- NO_LIVE\n")
        f.write("- PAPER_ONLY\n")
    print(f"Markdown report: {md_path}")

    print(f"\nStatus: PAPER_MULTI_FIXTURE_REPLAY_COMPLETE")
    return 0 if err_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
