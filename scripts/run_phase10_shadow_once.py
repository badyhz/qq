"""Phase 10 local shadow run — one-shot with local/mock data. No network."""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.data_source import DataSourceConfig, create_data_source
from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord
from core.paper_trading.shadow_gate_evaluator import evaluate_shadow_gate

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")
FIXTURE_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "paper_trading")

SAFETY_FLAGS = ["PAPER_ONLY", "READONLY_ONLY", "NO_REAL_HTTP", "NO_ORDER",
                "NO_TESTNET", "NO_LIVE", "NO_SECRET", "LOCAL_OR_MOCK_DATA_ONLY"]


def run_local_shadow():
    """Run a single local shadow pass using fixtures."""
    print("=== Phase 10 Local Shadow Run ===\n")
    os.makedirs(REPORT_DIR, exist_ok=True)

    ledger_path = os.path.join(REPORT_DIR, "phase10_shadow_ledger.jsonl")
    ledger = ShadowLedger(ledger_path)

    # Use existing fixture
    fixture_path = os.path.join(FIXTURE_DIR, "macd_rebound_sample.json")
    if not os.path.isfile(fixture_path):
        print(f"ERROR: Fixture not found: {fixture_path}")
        return 1

    config = DataSourceConfig(mode="fixture", fixture_path=fixture_path)
    source = create_data_source(config)
    bars = source.get_bars("BTCUSDT", limit=100)
    print(f"Loaded {len(bars)} bars from fixture")

    # Generate mock shadow records
    timestamp = time.time()
    records = []

    # Simulate some HIGH priority wins
    for i in range(8):
        records.append(ShadowRecord(
            timestamp=timestamp + i,
            symbol="BTCUSDT",
            timeframe="1h",
            priority="HIGH",
            signal_type="macd_rebound",
            plan_id=f"shadow_high_{i}",
            valid_plan=True,
            reject_reason="",
            entry=50000.0 + i * 100,
            stop=49000.0 + i * 100,
            take_profit=52000.0 + i * 100,
            rr=2.0,
            outcome="WIN",
            pnl=2000.0,
            expectancy_input=500.0,
            data_quality_ok=True,
            safety_flags=SAFETY_FLAGS,
        ))

    # Simulate some MEDIUM priority wins
    for i in range(12):
        records.append(ShadowRecord(
            timestamp=timestamp + 100 + i,
            symbol="BTCUSDT",
            timeframe="1h",
            priority="MEDIUM",
            signal_type="macd_rebound",
            plan_id=f"shadow_med_{i}",
            valid_plan=True,
            reject_reason="",
            entry=50000.0 + i * 50,
            stop=49500.0 + i * 50,
            take_profit=51000.0 + i * 50,
            rr=1.5,
            outcome="WIN",
            pnl=1000.0,
            expectancy_input=300.0,
            data_quality_ok=True,
            safety_flags=SAFETY_FLAGS,
        ))

    # Simulate some LOW priority mixed results
    for i in range(10):
        outcome = "WIN" if i % 3 == 0 else "LOSS"
        pnl = 200.0 if outcome == "WIN" else -150.0
        records.append(ShadowRecord(
            timestamp=timestamp + 200 + i,
            symbol="BTCUSDT",
            timeframe="1h",
            priority="LOW",
            signal_type="macd_rebound",
            plan_id=f"shadow_low_{i}",
            valid_plan=True,
            reject_reason="",
            entry=50000.0 + i * 20,
            stop=49800.0 + i * 20,
            take_profit=50400.0 + i * 20,
            rr=1.0,
            outcome=outcome,
            pnl=pnl,
            expectancy_input=50.0 if outcome == "WIN" else -50.0,
            data_quality_ok=True,
            safety_flags=SAFETY_FLAGS,
        ))

    # Write records
    for r in records:
        ledger.append(r)

    print(f"Generated {len(records)} shadow records")

    # Evaluate gate
    gate_result = evaluate_shadow_gate(ledger)
    print(f"\nGate Decision: {gate_result.decision}")
    print(f"Valid Plans: {gate_result.valid_plans}")
    print(f"HIGH: {gate_result.high_count}, MEDIUM: {gate_result.medium_count}, LOW: {gate_result.low_count}")
    print(f"Total Expectancy: {gate_result.total_expectancy}")
    print(f"Profit Factor: {gate_result.profit_factor}")
    print(f"Safety Violations: {gate_result.safety_violations}")

    # Generate summary JSON
    summary = ledger.summary()
    summary["gate_decision"] = gate_result.decision
    summary["gate_reasons"] = gate_result.reasons
    summary["safety_flags"] = SAFETY_FLAGS
    summary["data_source"] = "local_fixture"
    summary["network_enabled"] = False

    json_path = os.path.join(REPORT_DIR, "phase10_shadow_summary.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nJSON: {json_path}")

    # Generate summary markdown
    md_path = os.path.join(REPORT_DIR, "phase10_shadow_summary.md")
    with open(md_path, "w") as f:
        f.write("# Phase 10 Local Shadow Summary\n\n")
        f.write(f"**Data Source:** local_fixture (mock)\n")
        f.write(f"**Network Enabled:** False\n")
        f.write(f"**Gate Decision:** {gate_result.decision}\n\n")
        f.write("## Safety Flags\n\n")
        for flag in SAFETY_FLAGS:
            f.write(f"- {flag}\n")
        f.write(f"\n## Metrics\n\n")
        f.write(f"- Valid Plans: {gate_result.valid_plans}\n")
        f.write(f"- HIGH: {gate_result.high_count}\n")
        f.write(f"- MEDIUM: {gate_result.medium_count}\n")
        f.write(f"- LOW: {gate_result.low_count}\n")
        f.write(f"- Total Expectancy: {gate_result.total_expectancy}\n")
        f.write(f"- Profit Factor: {gate_result.profit_factor}\n")
        f.write(f"- Max Drawdown: {gate_result.max_drawdown}\n")
        f.write(f"- Safety Violations: {gate_result.safety_violations}\n")
        f.write(f"\n## Gate Reasons\n\n")
        for reason in gate_result.reasons:
            f.write(f"- {reason}\n")
    print(f"Markdown: {md_path}")

    print("\n=== Local Shadow Run Complete ===")
    print("\nSafety:")
    print("- No network calls")
    print("- No secret reads")
    print("- No order paths")
    print("- No testnet/live")
    return 0


if __name__ == "__main__":
    sys.exit(run_local_shadow())
