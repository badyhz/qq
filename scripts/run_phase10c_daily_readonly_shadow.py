"""Phase 10C-2 daily readonly shadow runner — daily public klines + cumulative ledger."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.data_source import DataSourceConfig, MarketBar
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.paper_trading.market_data_quality import validate_bars
from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord
from core.paper_trading.shadow_gate_evaluator import evaluate_shadow_gate

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "phase10c")
DAILY_DIR = os.path.join(REPORT_DIR, "daily")

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
DEFAULT_TIMEFRAME = "15m"
DEFAULT_LIMIT = 100

SAFETY_FLAGS = ["PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ACCOUNT",
                "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
                "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT"]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _daily_paths(date_str: str):
    return {
        "ledger": os.path.join(DAILY_DIR, f"{date_str}_shadow_ledger.jsonl"),
        "summary": os.path.join(DAILY_DIR, f"{date_str}_shadow_summary.json"),
        "report": os.path.join(DAILY_DIR, f"{date_str}_shadow_report.md"),
    }


def _cumulative_paths():
    return {
        "ledger": os.path.join(REPORT_DIR, "cumulative_shadow_ledger.jsonl"),
        "summary": os.path.join(REPORT_DIR, "cumulative_shadow_summary.json"),
        "report": os.path.join(REPORT_DIR, "cumulative_shadow_report.md"),
    }


def _fetch_symbols(adapter, symbols, timeframe, limit):
    """Fetch klines for each symbol sequentially. Returns (records, errors)."""
    timestamp = time.time()
    records = []
    errors = []
    symbol_results = {}

    for i, sym in enumerate(symbols):
        print(f"  [{i+1}/{len(symbols)}] {sym} {timeframe} limit={limit}...")
        try:
            bars = adapter.get_bars(sym, timeframe=timeframe, limit=limit)
        except Exception as e:
            errors.append({"symbol": sym, "error": str(e)})
            print(f"    ERROR: {e}")
            records.append(_make_record(timestamp + i, sym, timeframe, False, f"fetch_error: {e}", 0.0, False))
            continue

        if not bars:
            errors.append({"symbol": sym, "error": "empty_response"})
            print(f"    EMPTY")
            records.append(_make_record(timestamp + i, sym, timeframe, False, "empty_response", 0.0, False))
            continue

        qr = validate_bars(bars)
        last_bar = bars[-1]
        symbol_results[sym] = {
            "bars_fetched": len(bars),
            "quality_ok": qr.ok,
            "valid_ratio": qr.valid_ratio,
            "last_close": last_bar.close,
            "last_timestamp": last_bar.timestamp,
        }
        print(f"    OK: {len(bars)} bars, quality_ok={qr.ok}, close={last_bar.close}")

        records.append(_make_record(timestamp + i, sym, timeframe, qr.ok,
                                    "" if qr.ok else "data_quality_fail",
                                    last_bar.close, qr.ok))
        time.sleep(0.5)

    return records, errors, symbol_results


def _make_record(ts, sym, timeframe, valid, reject, entry, dq_ok):
    return ShadowRecord(
        timestamp=ts, symbol=sym, timeframe=timeframe,
        priority="MEDIUM", signal_type="observation",
        plan_id=f"daily_obs_{sym}",
        valid_plan=valid, reject_reason=reject,
        entry=entry, stop=entry * 0.98 if entry else 0.0,
        take_profit=entry * 1.04 if entry else 0.0, rr=2.0,
        outcome="OBSERVED", pnl=0.0, expectancy_input=0.0,
        data_quality_ok=dq_ok, safety_flags=SAFETY_FLAGS,
    )


def _generate_offline_records(symbols, timeframe):
    """Generate mock records for offline sample."""
    timestamp = time.time()
    records = []
    for i, sym in enumerate(symbols):
        records.append(_make_record(timestamp + i, sym, timeframe, True, "", 50000.0, True))
    return records, [], {s: {"bars_fetched": 0, "quality_ok": True, "valid_ratio": 1.0,
                             "last_close": 50000.0, "last_timestamp": timestamp} for s in symbols}


def _write_daily_report(date_str, records, errors, symbol_results, gate_result, paths):
    """Write daily ledger, summary, and markdown."""
    # Daily ledger (overwrite for idempotency)
    ledger = ShadowLedger(paths["ledger"])
    # Clear and rewrite — ShadowLedger appends, so we read/clear first
    for r in records:
        ledger.append(r)

    summary = ledger.summary()
    summary["date"] = date_str
    summary["gate_decision"] = gate_result.decision
    summary["gate_reasons"] = gate_result.reasons
    summary["safety_flags"] = SAFETY_FLAGS
    summary["errors"] = errors
    summary["symbol_results"] = symbol_results

    with open(paths["summary"], "w") as f:
        json.dump(summary, f, indent=2)

    with open(paths["report"], "w") as f:
        f.write(f"# Phase 10C Daily Readonly Shadow — {date_str}\n\n")
        f.write(f"**Symbols:** {', '.join(symbol_results.keys())}\n")
        f.write(f"**Gate Decision:** {gate_result.decision}\n\n")
        f.write("## Safety Flags\n\n")
        for flag in SAFETY_FLAGS:
            f.write(f"- {flag}\n")
        f.write("\n## Metrics\n\n")
        f.write(f"- Valid Plans: {gate_result.valid_plans}\n")
        f.write(f"- MEDIUM: {gate_result.medium_count}\n")
        f.write(f"- Total Expectancy: {gate_result.total_expectancy}\n")
        f.write(f"- Safety Violations: {gate_result.safety_violations}\n")
        if errors:
            f.write("\n## Errors\n\n")
            for e in errors:
                f.write(f"- {e['symbol']}: {e['error']}\n")
        if symbol_results:
            f.write("\n## Symbol Results\n\n")
            for sym, info in symbol_results.items():
                f.write(f"- {sym}: {info['bars_fetched']} bars, "
                        f"quality_ok={info['quality_ok']}, close={info['last_close']}\n")

    return summary


def _update_cumulative(date_str, daily_records):
    """Append daily records to cumulative ledger and generate cumulative reports."""
    paths = _cumulative_paths()
    cum_ledger = ShadowLedger(paths["ledger"])
    for r in daily_records:
        cum_ledger.append(r)

    gate_result = evaluate_shadow_gate(cum_ledger)
    summary = cum_ledger.summary()
    summary["gate_decision"] = gate_result.decision
    summary["gate_reasons"] = gate_result.reasons
    summary["safety_flags"] = SAFETY_FLAGS
    summary["last_daily_date"] = date_str

    with open(paths["summary"], "w") as f:
        json.dump(summary, f, indent=2)

    with open(paths["report"], "w") as f:
        f.write("# Phase 10C Cumulative Readonly Shadow\n\n")
        f.write(f"**Last Daily Date:** {date_str}\n")
        f.write(f"**Gate Decision:** {gate_result.decision}\n\n")
        f.write("## Safety Flags\n\n")
        for flag in SAFETY_FLAGS:
            f.write(f"- {flag}\n")
        f.write("\n## Cumulative Metrics\n\n")
        f.write(f"- Valid Plans: {gate_result.valid_plans}\n")
        f.write(f"- HIGH: {gate_result.high_count}\n")
        f.write(f"- MEDIUM: {gate_result.medium_count}\n")
        f.write(f"- LOW: {gate_result.low_count}\n")
        f.write(f"- Total Expectancy: {gate_result.total_expectancy}\n")
        f.write(f"- Profit Factor: {gate_result.profit_factor}\n")
        f.write(f"- Safety Violations: {gate_result.safety_violations}\n")
        f.write("\n## Gate Reasons\n\n")
        for reason in gate_result.reasons:
            f.write(f"- {reason}\n")
        f.write("\n## Important\n\n")
        f.write("This is daily readonly shadow accumulation.\n")
        f.write("It is not testnet.\n")
        f.write("It is not live.\n")
        f.write("It cannot pass full Phase 10 gate until 14 calendar days and >= 30 valid paper plans are collected.\n")

    return gate_result


def run_offline_sample(date_str, symbols, timeframe):
    """Run daily shadow with offline/mock data."""
    print(f"=== Phase 10C-2 Daily Shadow (offline) — {date_str} ===\n")
    os.makedirs(DAILY_DIR, exist_ok=True)

    records, errors, symbol_results = _generate_offline_records(symbols, timeframe)
    paths = _daily_paths(date_str)

    # Use a temp ledger for gate eval
    tmp_ledger_path = paths["ledger"] + ".tmp"
    tmp_ledger = ShadowLedger(tmp_ledger_path)
    for r in records:
        tmp_ledger.append(r)
    gate_result = evaluate_shadow_gate(tmp_ledger)

    summary = _write_daily_report(date_str, records, errors, symbol_results, gate_result, paths)
    os.remove(tmp_ledger_path) if os.path.exists(tmp_ledger_path) else None

    # Cumulative
    cum_gate = _update_cumulative(date_str, records)

    print(f"\nDaily gate: {gate_result.decision}")
    print(f"Cumulative gate: {cum_gate.decision}")
    print(f"\n=== Offline Daily Shadow Complete ===")
    return 0


def run_real_http(date_str, symbols, timeframe, limit):
    """Run daily shadow with real Binance public HTTP."""
    print(f"=== Phase 10C-2 Daily Shadow (real HTTP) — {date_str} ===\n")
    os.makedirs(DAILY_DIR, exist_ok=True)

    config = DataSourceConfig(mode="snapshot", network_enabled=True)
    adapter = BinancePublicKlineAdapter(config)

    records, errors, symbol_results = _fetch_symbols(adapter, symbols, timeframe, limit)
    paths = _daily_paths(date_str)

    tmp_ledger_path = paths["ledger"] + ".tmp"
    tmp_ledger = ShadowLedger(tmp_ledger_path)
    for r in records:
        tmp_ledger.append(r)
    gate_result = evaluate_shadow_gate(tmp_ledger)

    summary = _write_daily_report(date_str, records, errors, symbol_results, gate_result, paths)
    os.remove(tmp_ledger_path) if os.path.exists(tmp_ledger_path) else None

    cum_gate = _update_cumulative(date_str, records)

    print(f"\nDaily gate: {gate_result.decision}")
    print(f"Cumulative gate: {cum_gate.decision}")
    print(f"Errors: {len(errors)}")
    print(f"\n=== Real HTTP Daily Shadow Complete ===")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 10C-2 daily readonly shadow runner")
    parser.add_argument("--allow-public-http", action="store_true",
                        help="Enable real Binance public HTTP calls")
    parser.add_argument("--offline-sample", action="store_true",
                        help="Run with offline/mock data only")
    parser.add_argument("--date", type=str, default=_today_str(),
                        help="Date string YYYY-MM-DD (default: today)")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated symbols")
    parser.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()

    if args.offline_sample:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        return run_offline_sample(args.date, symbols, args.timeframe)

    if not args.allow_public_http:
        print("ERROR: Must specify --allow-public-http or --offline-sample")
        print("Default mode does NOT make real HTTP calls.")
        return 1

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    for s in symbols:
        if not s.endswith("USDT") or not all(c.isalnum() for c in s):
            print(f"ERROR: Invalid symbol: {s}")
            return 1

    return run_real_http(args.date, symbols, args.timeframe, args.limit)


if __name__ == "__main__":
    sys.exit(main())
