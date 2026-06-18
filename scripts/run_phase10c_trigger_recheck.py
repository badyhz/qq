"""Phase 10C-3H trigger recheck — re-evaluate watch candidates against current market data."""
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
from core.paper_trading.watch_trigger_planner import plan_trigger, WatchTriggerPlan
from core.paper_trading.watch_trigger_recheck import recheck_trigger, TriggerRecheckResult
from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "phase10c", "emergency")

DEFAULT_SYMBOLS = [
    "BNBUSDT", "DOGEUSDT", "AVAXUSDT", "SUIUSDT", "ARBUSDT",
    "TIAUSDT", "APTUSDT", "1000PEPEUSDT", "XRPUSDT",
]
DEFAULT_TIMEFRAMES = ["5m", "15m", "1h"]
DEFAULT_LIMIT = 120

SAFETY_FLAGS = ["PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ACCOUNT",
                "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
                "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT"]

RECHECK_STATUS_ORDER = ["TRIGGERED", "WAITING", "INVALIDATED",
                        "SHORT_TRIGGERED", "SHORT_WAITING", "SHORT_INVALIDATED", "DATA_ERROR"]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _fetch_recheck(adapter, symbols, timeframes, limit):
    """Fetch klines and recheck each symbol/timeframe."""
    results: list[TriggerRecheckResult] = []
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
                results.append(TriggerRecheckResult(
                    symbol=sym, timeframe=tf, previous_action_label="UNKNOWN",
                    current_watch_state="DATA_REJECT", current_setup_type="NO_TRADE",
                    last_close=0.0, recheck_status="DATA_ERROR",
                    trigger_reason="", invalidation_reason=str(e),
                    next_action="DATA_SKIP", risk_note="fetch error",
                ))
                print(f"ERROR: {e}")
                continue

            if not bars:
                errors.append({"symbol": sym, "timeframe": tf, "error": "empty"})
                results.append(TriggerRecheckResult(
                    symbol=sym, timeframe=tf, previous_action_label="UNKNOWN",
                    current_watch_state="DATA_REJECT", current_setup_type="NO_TRADE",
                    last_close=0.0, recheck_status="DATA_ERROR",
                    trigger_reason="", invalidation_reason="empty response",
                    next_action="DATA_SKIP", risk_note="empty response",
                ))
                print("EMPTY")
                continue

            qr = validate_bars(bars)
            if not qr.ok:
                results.append(TriggerRecheckResult(
                    symbol=sym, timeframe=tf, previous_action_label="UNKNOWN",
                    current_watch_state="DATA_REJECT", current_setup_type="NO_TRADE",
                    last_close=bars[-1].close, recheck_status="DATA_ERROR",
                    trigger_reason="", invalidation_reason=f"quality: {qr.issues[:3]}",
                    next_action="DATA_SKIP", risk_note="data quality fail",
                ))
                print(f"QUALITY_FAIL")
                continue

            sig = analyze_bars(bars)
            if sig is None:
                print("ANALYSIS_FAIL")
                continue

            recheck = recheck_trigger(sig, None)
            results.append(recheck)
            print(f"OK → {recheck.recheck_status} ({recheck.current_watch_state})")
            time.sleep(0.3)

    return results, errors


def _generate_offline_results(symbols, timeframes):
    """Generate mock recheck results for offline sample."""
    results = []
    statuses = ["TRIGGERED", "WAITING", "INVALIDATED", "SHORT_TRIGGERED", "WAITING",
                "WAITING", "SHORT_INVALIDATED", "WAITING", "DATA_ERROR"]
    for i, sym in enumerate(symbols):
        for tf in timeframes:
            st = statuses[i % len(statuses)]
            results.append(TriggerRecheckResult(
                symbol=sym, timeframe=tf,
                previous_action_label="WAIT_CONFIRMATION" if st != "SHORT_TRIGGERED" else "SHORT_OBSERVE",
                current_watch_state="LONG_READY" if st == "TRIGGERED" else "NEAR_TURN_UP" if st == "WAITING" else "WEAK_AVOID",
                current_setup_type="NO_TRADE", last_close=50000.0 + i * 100,
                recheck_status=st,
                trigger_reason="mock" if "TRIGGERED" in st else "",
                invalidation_reason="mock" if "INVALIDATED" in st else "",
                next_action="OBSERVE_NOW" if st == "TRIGGERED" else "KEEP_WAITING" if st == "WAITING" else "DROP_FROM_WATCH",
                risk_note="offline mock",
            ))
    return results, []


def _result_to_dict(r: TriggerRecheckResult) -> dict:
    return {
        "symbol": r.symbol, "timeframe": r.timeframe,
        "previous_action_label": r.previous_action_label,
        "current_watch_state": r.current_watch_state,
        "current_setup_type": r.current_setup_type,
        "last_close": r.last_close,
        "recheck_status": r.recheck_status,
        "trigger_reason": r.trigger_reason,
        "invalidation_reason": r.invalidation_reason,
        "next_action": r.next_action,
        "risk_note": r.risk_note,
    }


def _to_shadow_record(r: TriggerRecheckResult, ts: float) -> ShadowRecord:
    priority = "MEDIUM" if r.recheck_status in ("TRIGGERED", "SHORT_TRIGGERED") else "LOW"
    return ShadowRecord(
        timestamp=ts, symbol=r.symbol, timeframe=r.timeframe,
        priority=priority, signal_type="trigger_recheck",
        plan_id=f"recheck_{r.symbol}_{r.timeframe}",
        valid_plan=r.recheck_status not in ("DATA_ERROR",),
        reject_reason=r.invalidation_reason if r.invalidation_reason else "",
        entry=r.last_close, stop=0.0, take_profit=0.0, rr=0.0,
        outcome="OBSERVED", pnl=0.0, expectancy_input=0.0,
        data_quality_ok=r.recheck_status != "DATA_ERROR",
        safety_flags=SAFETY_FLAGS,
    )


def _write_reports(date_str, results, errors, mode):
    """Write JSON, MD, CSV, and shadow ledger."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    by_status: dict[str, list[TriggerRecheckResult]] = {s: [] for s in RECHECK_STATUS_ORDER}
    for r in results:
        s = r.recheck_status if r.recheck_status in by_status else "DATA_ERROR"
        by_status[s].append(r)

    status_counts = {s: len(lst) for s, lst in by_status.items()}

    # JSON
    json_data = {
        "date": date_str, "mode": mode, "safety_flags": SAFETY_FLAGS,
        "total_rechecked": len(results),
        "status_counts": status_counts,
        "errors": errors,
        "results": [_result_to_dict(r) for r in results],
    }
    json_path = os.path.join(REPORT_DIR, f"{date_str}_trigger_recheck.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"\nJSON: {json_path}")

    # CSV
    csv_path = os.path.join(REPORT_DIR, f"{date_str}_trigger_recheck.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "timeframe", "previous_action", "current_watch_state",
                         "recheck_status", "last_close", "next_action",
                         "trigger_reason", "invalidation_reason", "risk_note"])
        for r in results:
            writer.writerow([r.symbol, r.timeframe, r.previous_action_label,
                             r.current_watch_state, r.recheck_status, r.last_close,
                             r.next_action, r.trigger_reason, r.invalidation_reason, r.risk_note])
    print(f"CSV: {csv_path}")

    # Shadow ledger
    ledger_path = os.path.join(REPORT_DIR, f"{date_str}_trigger_recheck_ledger.jsonl")
    ledger = ShadowLedger(ledger_path)
    ts = time.time()
    for i, r in enumerate(results):
        ledger.append(_to_shadow_record(r, ts + i))
    print(f"Shadow ledger: {ledger_path}")

    # Markdown
    md_path = os.path.join(REPORT_DIR, f"{date_str}_trigger_recheck.md")
    with open(md_path, "w") as f:
        f.write(f"# Trigger Recheck Report — {date_str}\n\n")
        f.write(f"**Mode:** {mode}\n")
        f.write(f"**Rechecked:** {len(results)} symbol/timeframe combinations\n\n")

        f.write("## Status Summary\n\n")
        f.write("| Status | Count |\n|---|---|\n")
        for s in RECHECK_STATUS_ORDER:
            if status_counts[s] > 0:
                f.write(f"| {s} | {status_counts[s]} |\n")

        for status_name, label in [
            ("TRIGGERED", "## TRIGGERED — Ready to Observe"),
            ("SHORT_TRIGGERED", "## SHORT_TRIGGERED — Bearish Confirmed"),
            ("WAITING", "## WAITING — Still Waiting"),
            ("SHORT_WAITING", "## SHORT_WAITING — Bearish Waiting"),
            ("INVALIDATED", "## INVALIDATED — Dropped"),
            ("SHORT_INVALIDATED", "## SHORT_INVALIDATED — Bearish Setup Broken"),
            ("DATA_ERROR", "## DATA_ERROR — Data Issues"),
        ]:
            if by_status[status_name]:
                f.write(f"\n{label}\n\n")
                for r in by_status[status_name]:
                    _write_recheck_md(f, r)

        f.write("\n## Safety\n\n")
        f.write("Readonly observation only.\n")
        f.write("Not a trading recommendation.\n")
        f.write("Not testnet/live.\n")
        f.write("No orders placed. No accounts accessed.\n")

        if errors:
            f.write("\n## Errors\n\n")
            for e in errors:
                f.write(f"- {e['symbol']} {e['timeframe']}: {e['error']}\n")
    print(f"Markdown: {md_path}")

    return status_counts


def _write_recheck_md(f, r: TriggerRecheckResult):
    f.write(f"### {r.symbol} ({r.timeframe}) — {r.recheck_status}\n\n")
    f.write(f"- **Previous:** {r.previous_action_label}\n")
    f.write(f"- **Current State:** {r.current_watch_state}\n")
    f.write(f"- **Last Close:** {r.last_close}\n")
    f.write(f"- **Next Action:** {r.next_action}\n")
    if r.trigger_reason:
        f.write(f"- **Trigger:** {r.trigger_reason}\n")
    if r.invalidation_reason:
        f.write(f"- **Invalidation:** {r.invalidation_reason}\n")
    f.write(f"- **Risk:** {r.risk_note}\n\n")


def run_offline(symbols, timeframes):
    print(f"=== Phase 10C-3H Trigger Recheck (offline) ===\n")
    results, errors = _generate_offline_results(symbols, timeframes)
    date_str = _today_str()
    counts = _write_reports(date_str, results, errors, "offline_sample")
    print(f"\nStatus counts:")
    for s, c in counts.items():
        if c > 0:
            print(f"  {s}: {c}")
    print("\n=== Offline Complete ===")
    return 0


def run_real_http(symbols, timeframes, limit):
    print(f"=== Phase 10C-3H Trigger Recheck (real HTTP) ===\n")
    config = DataSourceConfig(mode="snapshot", network_enabled=True)
    adapter = BinancePublicKlineAdapter(config)
    results, errors = _fetch_recheck(adapter, symbols, timeframes, limit)
    date_str = _today_str()
    counts = _write_reports(date_str, results, errors, "real_public_http")
    print(f"\nStatus counts:")
    for s, c in counts.items():
        if c > 0:
            print(f"  {s}: {c}")
    print(f"Errors: {len(errors)}")
    print("\n=== Real HTTP Complete ===")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 10C-3H trigger recheck")
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
