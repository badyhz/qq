"""Paper parameter sweep runner — local multi-parameter backtest, no network."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.parameter_sweep import (
    ParameterSet, SweepConfig, default_score, generate_default_param_sets, run_sweep,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "paper_trading")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def main():
    print("=== Paper Parameter Sweep Runner ===\n")

    # Find fixtures
    fixtures = sorted([
        os.path.join(FIXTURE_DIR, f)
        for f in os.listdir(FIXTURE_DIR)
        if f.endswith(".json") and f not in ("empty_sample.json", "malformed_sample.json")
    ])
    print(f"Fixtures: {len(fixtures)}")

    # Generate param sets
    param_sets = generate_default_param_sets()
    print(f"Parameter combinations: {len(param_sets)}\n")

    config = SweepConfig(
        fixtures=fixtures,
        param_sets=param_sets,
    )

    results = run_sweep(config)

    # Print top 10
    print("=== Top 10 Parameter Sets ===\n")
    for i, r in enumerate(results[:10]):
        print(f"  #{i+1} score={r.score:.1f}  "
              f"trades={r.metrics.total_trades}  "
              f"win_rate={r.metrics.win_rate:.1%}  "
              f"pnl={r.metrics.total_pnl:.0f}  "
              f"pf={r.metrics.profit_factor:.2f}  "
              f"dd={r.metrics.max_drawdown:.0f}")
        print(f"       {r.params.label()}")
    print()

    # JSON output
    os.makedirs(REPORT_DIR, exist_ok=True)
    json_path = os.path.join(REPORT_DIR, "paper_trading_parameter_sweep.json")
    json_data = {
        "total_param_sets": len(param_sets),
        "total_fixtures": len(fixtures),
        "results": [
            {
                "rank": i + 1,
                "params": {
                    "min_rr_ratio": r.params.min_rr_ratio,
                    "max_risk_per_trade_pct": r.params.max_risk_per_trade_pct,
                    "max_position_pct": r.params.max_position_pct,
                    "trailing_stop_pct": r.params.trailing_stop_pct,
                    "take_profit_pct": r.params.take_profit_pct,
                    "stop_loss_pct": r.params.stop_loss_pct,
                    "time_stop_bars": r.params.time_stop_bars,
                },
                "score": r.score,
                "total_trades": r.metrics.total_trades,
                "win_rate": round(r.metrics.win_rate, 4),
                "total_pnl": round(r.metrics.total_pnl, 2),
                "profit_factor": round(r.metrics.profit_factor, 2) if r.metrics.profit_factor != float("inf") else "inf",
                "max_drawdown": round(r.metrics.max_drawdown, 2),
                "expectancy": round(r.metrics.expectancy, 2),
                "max_consecutive_losses": r.metrics.max_consecutive_losses,
                "fixtures_ok": r.fixtures_ok,
                "fixtures_error": r.fixtures_error,
            }
            for i, r in enumerate(results)
        ],
        "safety_flags": ["NO_REAL_ORDER", "NO_REAL_HTTP", "NO_SECRET_READ", "PAPER_ONLY"],
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"JSON: {json_path}")

    # Markdown output
    md_path = os.path.join(REPORT_DIR, "paper_trading_parameter_sweep.md")
    with open(md_path, "w") as f:
        f.write("# Paper Trading Parameter Sweep Report\n\n")
        f.write(f"**Date:** 2026-06-16\n")
        f.write(f"**Mode:** paper-only / local / no network\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Parameter combinations | {len(param_sets)} |\n")
        f.write(f"| Fixtures | {len(fixtures)} |\n")
        f.write(f"| Top score | {results[0].score:.1f} |\n\n")
        f.write("## Top 10\n\n")
        f.write("| Rank | Score | Trades | Win Rate | PnL | PF | Max DD | Params |\n")
        f.write("|------|-------|--------|----------|-----|----|----|--------|\n")
        for i, r in enumerate(results[:10]):
            pf = f"{r.metrics.profit_factor:.1f}" if r.metrics.profit_factor != float("inf") else "inf"
            f.write(f"| {i+1} | {r.score:.1f} | {r.metrics.total_trades} | "
                    f"{r.metrics.win_rate:.1%} | {r.metrics.total_pnl:.0f} | "
                    f"{pf} | {r.metrics.max_drawdown:.0f} | "
                    f"rr={r.params.min_rr_ratio} tp={r.params.take_profit_pct} "
                    f"sl={r.params.stop_loss_pct} |\n")
        f.write("\n## Safety\n\n")
        f.write("- NO_REAL_ORDER\n- NO_REAL_HTTP\n- NO_SECRET_READ\n- PAPER_ONLY\n")
    print(f"Markdown: {md_path}")

    print(f"\nStatus: PAPER_PARAMETER_SWEEP_COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
