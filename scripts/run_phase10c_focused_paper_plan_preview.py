"""Phase 10C-3I focused paper plan preview — generate paper-only trade plan previews for focused symbols."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.data_source import DataSourceConfig
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.paper_trading.market_data_quality import validate_bars
from core.paper_trading.readonly_signal_analyzer import analyze_bars, SignalResult
from core.paper_trading.watch_trigger_recheck import recheck_trigger, TriggerRecheckResult
from core.paper_trading.focused_paper_plan_preview import preview_plan, FocusedPaperPlan, SAFETY_FLAGS
from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "phase10c", "emergency")

DEFAULT_SYMBOLS = ["BNBUSDT", "SUIUSDT", "XRPUSDT", "ARBUSDT"]
DEFAULT_TIMEFRAMES = ["5m", "15m", "1h"]
DEFAULT_LIMIT = 120


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _fetch_and_preview(adapter, symbols, timeframes, limit):
    """Fetch klines, analyze, recheck, and preview plans."""
    plans: list[FocusedPaperPlan] = []
    errors = []
    fetch_count = 0
    total = len(symbols) * len(timeframes)

    for sym in symbols:
        for tf in timeframes:
            fetch_count += 1
            print(f"  [{fetch_count}/{total}] {sym} {tf}...", end=" ")
            try:
                bars = adapter.get_bars(sym, timeframe=tf, limit=limit)
            except Exception as e:
                errors.append({"symbol": sym, "timeframe": tf, "error": str(e)})
                print(f"ERROR: {e}")
                continue

            if not bars:
                errors.append({"symbol": sym, "timeframe": tf, "error": "empty"})
                print("EMPTY")
                continue

            qr = validate_bars(bars)
            if not qr.ok:
                errors.append({"symbol": sym, "timeframe": tf, "error": f"quality: {qr.issues[:3]}"})
                print("QUALITY_FAIL")
                continue

            sig = analyze_bars(bars)
            if sig is None:
                print("ANALYSIS_FAIL")
                continue

            recheck = recheck_trigger(sig, None)
            plan = preview_plan(sig, recheck)
            plans.append(plan)
            print(f"OK → {plan.plan_decision} ({plan.direction}, rr={plan.rr_ratio})")
            time.sleep(0.3)

    return plans, errors


def _generate_offline_results(symbols, timeframes):
    """Generate mock plans for offline sample."""
    plans = []
    decisions = ["WATCH", "WAIT", "AVOID", "WATCH", "WAIT", "AVOID", "WATCH", "WAIT"]
    directions = ["LONG_OBSERVE", "LONG_OBSERVE", "NO_TRADE", "SHORT_OBSERVE",
                   "LONG_OBSERVE", "NO_TRADE", "LONG_OBSERVE", "NO_TRADE"]
    statuses = ["TRIGGERED", "WAITING", "INVALIDATED", "SHORT_TRIGGERED",
                "WAITING", "DATA_ERROR", "TRIGGERED", "SHORT_INVALIDATED"]

    for i, sym in enumerate(symbols):
        for j, tf in enumerate(timeframes):
            idx = (i + j) % len(decisions)
            plans.append(FocusedPaperPlan(
                symbol=sym, timeframe=tf,
                direction=directions[idx],
                source_status=statuses[idx],
                last_close=600.0 + i * 10,
                entry_observation=600.0 + i * 10,
                invalidation_level=590.0 + i * 10,
                take_profit_observation=620.0 + i * 10 if directions[idx] != "NO_TRADE" else 0.0,
                rr_ratio=2.0 if directions[idx] != "NO_TRADE" else 0.0,
                risk_distance_pct=1.67,
                reward_distance_pct=3.33 if directions[idx] != "NO_TRADE" else 0.0,
                plan_decision=decisions[idx],
                reason=f"offline mock: {statuses[idx]}",
                safety_flags=list(SAFETY_FLAGS),
            ))
    return plans, []


def _plan_to_dict(p: FocusedPaperPlan) -> dict:
    return {
        "symbol": p.symbol, "timeframe": p.timeframe,
        "direction": p.direction, "source_status": p.source_status,
        "last_close": p.last_close,
        "entry_observation": p.entry_observation,
        "invalidation_level": p.invalidation_level,
        "take_profit_observation": p.take_profit_observation,
        "rr_ratio": p.rr_ratio,
        "risk_distance_pct": p.risk_distance_pct,
        "reward_distance_pct": p.reward_distance_pct,
        "plan_decision": p.plan_decision,
        "reason": p.reason,
        "safety_flags": p.safety_flags,
    }


def _to_shadow_record(p: FocusedPaperPlan, ts: float) -> ShadowRecord:
    priority = "HIGH" if p.plan_decision == "WATCH" else "MEDIUM" if p.plan_decision == "WAIT" else "LOW"
    return ShadowRecord(
        timestamp=ts, symbol=p.symbol, timeframe=p.timeframe,
        priority=priority, signal_type="focused_plan_preview",
        plan_id=f"preview_{p.symbol}_{p.timeframe}",
        valid_plan=p.plan_decision != "AVOID",
        reject_reason=p.reason if p.plan_decision == "AVOID" else "",
        entry=p.entry_observation, stop=p.invalidation_level,
        take_profit=p.take_profit_observation, rr=p.rr_ratio,
        outcome="OBSERVED", pnl=0.0, expectancy_input=0.0,
        data_quality_ok=p.source_status != "DATA_ERROR",
        safety_flags=p.safety_flags,
    )


def _write_reports(date_str, plans, errors, mode):
    """Write JSON, MD, CSV, and shadow ledger."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    by_decision: dict[str, list[FocusedPaperPlan]] = {"WATCH": [], "WAIT": [], "AVOID": []}
    for p in plans:
        d = p.plan_decision if p.plan_decision in by_decision else "AVOID"
        by_decision[d].append(p)

    decision_counts = {d: len(lst) for d, lst in by_decision.items()}

    # JSON
    json_data = {
        "date": date_str, "mode": mode, "safety_flags": SAFETY_FLAGS,
        "total_plans": len(plans),
        "decision_counts": decision_counts,
        "errors": errors,
        "plans": [_plan_to_dict(p) for p in plans],
    }
    json_path = os.path.join(REPORT_DIR, f"{date_str}_focused_paper_plan_preview.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"\nJSON: {json_path}")

    # CSV
    csv_path = os.path.join(REPORT_DIR, f"{date_str}_focused_paper_plan_preview.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "timeframe", "direction", "source_status", "last_close",
                         "entry_observation", "invalidation_level", "take_profit_observation",
                         "rr_ratio", "risk_distance_pct", "reward_distance_pct",
                         "plan_decision", "reason"])
        for p in plans:
            writer.writerow([p.symbol, p.timeframe, p.direction, p.source_status, p.last_close,
                             p.entry_observation, p.invalidation_level, p.take_profit_observation,
                             p.rr_ratio, p.risk_distance_pct, p.reward_distance_pct,
                             p.plan_decision, p.reason])
    print(f"CSV: {csv_path}")

    # Shadow ledger
    ledger_path = os.path.join(REPORT_DIR, f"{date_str}_focused_plan_preview_ledger.jsonl")
    ledger = ShadowLedger(ledger_path)
    ts = time.time()
    for i, p in enumerate(plans):
        ledger.append(_to_shadow_record(p, ts + i))
    print(f"Shadow ledger: {ledger_path}")

    # Markdown
    md_path = os.path.join(REPORT_DIR, f"{date_str}_focused_paper_plan_preview.md")
    with open(md_path, "w") as f:
        f.write(f"# Focused Paper Plan Preview — {date_str}\n\n")
        f.write(f"**Mode:** {mode}\n")
        f.write(f"**Plans:** {len(plans)} symbol/timeframe combinations\n\n")

        f.write("## Decision Summary\n\n")
        f.write("| Decision | Count |\n|---|---|\n")
        for d in ["WATCH", "WAIT", "AVOID"]:
            if decision_counts[d] > 0:
                f.write(f"| {d} | {decision_counts[d]} |\n")

        for decision, label in [
            ("WATCH", "## WATCH — Ready to Observe"),
            ("WAIT", "## WAIT — Waiting for Confirmation"),
            ("AVOID", "## AVOID — Not a Trade"),
        ]:
            if by_decision[decision]:
                f.write(f"\n{label}\n\n")
                for p in by_decision[decision]:
                    _write_plan_md(f, p)

        f.write("\n## Safety\n\n")
        f.write("Paper-only observation. No orders placed. No accounts accessed.\n")
        f.write("Not a trading recommendation. Not testnet/live.\n")

        if errors:
            f.write("\n## Errors\n\n")
            for e in errors:
                f.write(f"- {e['symbol']} {e['timeframe']}: {e['error']}\n")
    print(f"Markdown: {md_path}")

    return decision_counts


def _write_plan_md(f, p: FocusedPaperPlan):
    f.write(f"### {p.symbol} ({p.timeframe}) — {p.plan_decision}\n\n")
    f.write(f"- **Direction:** {p.direction}\n")
    f.write(f"- **Source Status:** {p.source_status}\n")
    f.write(f"- **Last Close:** {p.last_close}\n")
    f.write(f"- **Entry Observation:** {p.entry_observation}\n")
    f.write(f"- **Invalidation:** {p.invalidation_level}\n")
    f.write(f"- **Take Profit:** {p.take_profit_observation}\n")
    f.write(f"- **R:R:** {p.rr_ratio}\n")
    f.write(f"- **Risk Distance:** {p.risk_distance_pct}%\n")
    f.write(f"- **Reward Distance:** {p.reward_distance_pct}%\n")
    f.write(f"- **Reason:** {p.reason}\n\n")


def run_offline(symbols, timeframes):
    print(f"=== Phase 10C-3I Focused Paper Plan Preview (offline) ===\n")
    plans, errors = _generate_offline_results(symbols, timeframes)
    date_str = _today_str()
    counts = _write_reports(date_str, plans, errors, "offline_sample")
    print(f"\nDecision counts:")
    for d, c in counts.items():
        if c > 0:
            print(f"  {d}: {c}")
    print("\n=== Offline Complete ===")
    return 0


def run_real_http(symbols, timeframes, limit):
    print(f"=== Phase 10C-3I Focused Paper Plan Preview (real HTTP) ===\n")
    config = DataSourceConfig(mode="snapshot", network_enabled=True)
    adapter = BinancePublicKlineAdapter(config)
    plans, errors = _fetch_and_preview(adapter, symbols, timeframes, limit)
    date_str = _today_str()
    counts = _write_reports(date_str, plans, errors, "real_public_http")
    print(f"\nDecision counts:")
    for d, c in counts.items():
        if c > 0:
            print(f"  {d}: {c}")
    print(f"Errors: {len(errors)}")
    print("\n=== Real HTTP Complete ===")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 10C-3I focused paper plan preview")
    parser.add_argument("--allow-public-http", action="store_true")
    parser.add_argument("--offline-sample", action="store_true")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--timeframes", type=str, default=",".join(DEFAULT_TIMEFRAMES))
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip()]

    if args.offline_sample:
        return run_offline(symbols, timeframes)

    if not args.allow_public_http:
        print("ERROR: Must specify --allow-public-http or --offline-sample")
        return 1

    return run_real_http(symbols, timeframes, args.limit)


if __name__ == "__main__":
    sys.exit(main())
