"""Paper trading ops report — aggregates all local reports, no network."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def _load_json(filename: str) -> dict | None:
    path = os.path.join(REPORT_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def main():
    print("=== Paper Trading Ops Report Generator ===\n")

    # Load all available reports
    dry_run = _load_json("paper_trading_decision_engine_summary.json")
    multi_fixture = _load_json("paper_trading_multi_fixture_summary.json")
    param_sweep = _load_json("paper_trading_parameter_sweep.json")

    os.makedirs(REPORT_DIR, exist_ok=True)

    # Collect alerts
    alerts = []
    if dry_run:
        if dry_run.get("total_pnl", 0) < 0:
            alerts.append({"level": "WARNING", "category": "pnl", "message": f"Dry-run PnL negative: {dry_run['total_pnl']}"})
        mc = dry_run.get("performance_metrics", {}).get("max_consecutive_losses", 0)
        if mc >= 3:
            alerts.append({"level": "CRITICAL", "category": "risk", "message": f"Consecutive losses: {mc}"})
    if multi_fixture:
        err = multi_fixture.get("error_count", 0)
        if err > 0:
            alerts.append({"level": "WARNING", "category": "fixtures", "message": f"{err} fixture errors"})

    # Build ops report
    report = {
        "status": "PAPER_TRADING_OPS_COMPLETE",
        "dry_run": dry_run,
        "multi_fixture": multi_fixture,
        "parameter_sweep_top10": param_sweep["results"][:10] if param_sweep else [],
        "alerts": alerts,
        "safety_flags": ["NO_REAL_ORDER", "NO_REAL_HTTP", "NO_SECRET_READ", "NO_TESTNET", "NO_LIVE", "PAPER_ONLY"],
    }

    # JSON
    json_path = os.path.join(REPORT_DIR, "paper_trading_ops_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"JSON: {json_path}")

    # Markdown
    md_path = os.path.join(REPORT_DIR, "paper_trading_ops_report.md")
    with open(md_path, "w") as f:
        f.write("# Paper Trading Ops Report\n\n")
        f.write("**Date:** 2026-06-16\n")
        f.write("**Mode:** paper-only / local / no network\n\n")

        # Status
        f.write("## Current Status\n\n")
        if dry_run:
            f.write(f"- Dry-run PnL: {dry_run.get('total_pnl', 'N/A')}\n")
            f.write(f"- Dry-run trades: {dry_run.get('trades_executed', 'N/A')}\n")
            f.write(f"- Win rate: {dry_run.get('win_rate', 'N/A')}\n")
        if multi_fixture:
            f.write(f"- Multi-fixture total trades: {multi_fixture.get('total_trades', 'N/A')}\n")
            f.write(f"- Multi-fixture PnL: {multi_fixture.get('total_pnl', 'N/A')}\n")

        # Parameter sweep top 10
        if param_sweep:
            f.write("\n## Parameter Sweep Top 10\n\n")
            f.write("| Rank | Score | Trades | Win Rate | PnL | PF |\n")
            f.write("|------|-------|--------|----------|-----|----|\n")
            for r in param_sweep["results"][:10]:
                pf = r.get("profit_factor", "N/A")
                f.write(f"| {r['rank']} | {r['score']:.1f} | {r['total_trades']} | "
                        f"{r['win_rate']:.1%} | {r['total_pnl']:.0f} | {pf} |\n")

        # Alerts
        if alerts:
            f.write("\n## Alerts\n\n")
            for a in alerts:
                f.write(f"- [{a['level']}] {a['category']}: {a['message']}\n")

        # Safety
        f.write("\n## Safety\n\n")
        f.write("- NO_REAL_ORDER\n- NO_REAL_HTTP\n- NO_SECRET_READ\n")
        f.write("- NO_TESTNET\n- NO_LIVE\n- PAPER_ONLY\n")

        # Next steps
        f.write("\n## Next Steps\n\n")
        f.write("- Evaluate top parameter set for live paper trading\n")
        f.write("- Consider adding more fixtures for robustness\n")
        f.write("- Review alerts and risk explanations\n")
        f.write("- Do NOT proceed to testnet/live without human approval\n")

    print(f"Markdown: {md_path}")
    print(f"\nStatus: PAPER_TRADING_OPS_COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
