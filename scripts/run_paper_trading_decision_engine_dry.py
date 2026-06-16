"""Paper trading dry-run runner — local simulation only, no network."""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.order_plan import OrderSide, OrderStatus
from core.paper_trading.risk_sizing import RiskSizingConfig, apply_risk_sizing
from core.paper_trading.exit_rules import ExitRuleConfig
from core.paper_trading.signal_to_plan_adapter import signal_envelope_to_order_plan
from core.paper_trading.human_approval_gate import HumanApprovalGate
from core.paper_trading.replay_engine import (
    ReplayBar, ReplayConfig, load_bars_from_fixture, run_replay,
)
from core.paper_trading.alert_explainer import explain_alert, format_alert_text


FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "tests", "fixtures",
    "paper_trading", "macd_rebound_sample.json",
)
REPORT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "reports",
    "paper_trading_decision_engine_report.md",
)


def macd_rebound_signal(bars, i):
    """Simple MACD rebound signal simulation for dry-run."""
    if i < 10:
        return None
    # Simulate: buy when price drops 3% then recovers
    recent_high = max(b.high for b in bars[max(0, i-10):i])
    current = bars[i].close
    drop_pct = (recent_high - current) / recent_high * 100

    if drop_pct >= 3.0 and bars[i].close > bars[i].open:
        return {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "entry_price": current,
            "stop_loss": current * 0.98,
            "take_profit": current * 1.06,
            "invalidation_price": current * 0.97,
            "signal_source": "macd_rebound_dry",
        }
    return None


def main():
    print("=== Paper Trading Decision Engine — Dry Run ===")
    print()

    # Load fixture
    if not os.path.exists(FIXTURE_PATH):
        print(f"ERROR: Fixture not found: {FIXTURE_PATH}")
        sys.exit(1)

    bars = load_bars_from_fixture(FIXTURE_PATH)
    print(f"Loaded {len(bars)} bars from fixture")

    # Configure
    risk_config = RiskSizingConfig(
        max_risk_per_trade_pct=1.0,
        max_position_pct=10.0,
        min_rr_ratio=1.5,
        max_margin_cap=50000,
        equity=100000,
    )
    exit_config = ExitRuleConfig(
        stop_loss_pct=2.0,
        take_profit_pct=6.0,
        trailing_stop_pct=1.5,
        time_stop_bars=50,
    )
    replay_config = ReplayConfig(
        risk_config=risk_config,
        exit_config=exit_config,
        auto_approve=True,
    )

    # Run replay
    result = run_replay(bars, macd_rebound_signal, replay_config)

    print(f"Bars processed: {result.bars_processed}")
    print(f"Signals generated: {result.signals_generated}")
    print(f"Plans created: {result.plans_created}")
    print(f"Plans approved: {result.plans_approved}")
    print(f"Trades executed: {result.trades_executed}")
    print()

    # Ledger summary
    summary = result.ledger.summary()
    print("=== Ledger Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print()

    # Generate report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write("# Paper Trading Decision Engine — Dry Run Report\n\n")
        f.write(f"**Date:** 2026-06-16\n")
        f.write(f"**Mode:** paper-only / dry-run / no real orders\n\n")
        f.write("## Replay Results\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Bars processed | {result.bars_processed} |\n")
        f.write(f"| Signals generated | {result.signals_generated} |\n")
        f.write(f"| Plans created | {result.plans_created} |\n")
        f.write(f"| Plans approved | {result.plans_approved} |\n")
        f.write(f"| Trades executed | {result.trades_executed} |\n\n")
        f.write("## Ledger Summary\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        for k, v in summary.items():
            f.write(f"| {k} | {v} |\n")
        f.write("\n## Safety\n\n")
        f.write("- paper_only=true\n")
        f.write("- dry_run_only=true\n")
        f.write("- no real orders\n")
        f.write("- no network calls\n")
        f.write("- no webhook\n")

    print(f"Report written to: {REPORT_PATH}")
    print()
    print("Status: PAPER_TRADING_DRY_RUN_COMPLETE")
    print("No real orders placed. No network calls made.")


if __name__ == "__main__":
    main()
