"""Phase 10C-1 real readonly shadow once — one-shot public klines fetch + paper shadow."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.data_source import DataSourceConfig, MarketBar
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.paper_trading.market_data_quality import validate_bars
from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord
from core.paper_trading.shadow_gate_evaluator import evaluate_shadow_gate

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
DEFAULT_TIMEFRAME = "15m"
DEFAULT_LIMIT = 100

SAFETY_FLAGS = ["PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ACCOUNT",
                "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
                "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT"]


def run_offline_sample():
    """Run shadow once with offline/mock data (no HTTP)."""
    print("=== Phase 10C-1 Offline Sample ===\n")
    os.makedirs(REPORT_DIR, exist_ok=True)

    ledger_path = os.path.join(REPORT_DIR, "phase10c_real_readonly_shadow_ledger.jsonl")
    ledger = ShadowLedger(ledger_path)

    timestamp = time.time()
    records = []
    for i, sym in enumerate(DEFAULT_SYMBOLS):
        records.append(ShadowRecord(
            timestamp=timestamp + i,
            symbol=sym,
            timeframe=DEFAULT_TIMEFRAME,
            priority="MEDIUM",
            signal_type="observation",
            plan_id=f"offline_obs_{sym}",
            valid_plan=True,
            reject_reason="",
            entry=50000.0,
            stop=49000.0,
            take_profit=52000.0,
            rr=2.0,
            outcome="WIN",
            pnl=1000.0,
            expectancy_input=500.0,
            data_quality_ok=True,
            safety_flags=SAFETY_FLAGS,
        ))

    for r in records:
        ledger.append(r)

    gate_result = evaluate_shadow_gate(ledger)
    summary = ledger.summary()
    summary["gate_decision"] = gate_result.decision
    summary["gate_reasons"] = gate_result.reasons
    summary["safety_flags"] = SAFETY_FLAGS
    summary["mode"] = "offline_sample"
    summary["symbols"] = DEFAULT_SYMBOLS
    summary["timeframe"] = DEFAULT_TIMEFRAME
    summary["limit"] = DEFAULT_LIMIT
    summary["public_http"] = False

    json_path = os.path.join(REPORT_DIR, "phase10c_real_readonly_shadow_once.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"JSON: {json_path}")

    md_path = os.path.join(REPORT_DIR, "phase10c_real_readonly_shadow_once.md")
    with open(md_path, "w") as f:
        _write_md(f, summary, gate_result, "offline_sample", False)
    print(f"Markdown: {md_path}")

    print(f"\nGate Decision: {gate_result.decision}")
    print(f"Records: {len(records)}")
    print("\n=== Offline Sample Complete ===")
    return 0


def run_real_public_http(symbols, timeframe, limit):
    """Run shadow once with real Binance public HTTP."""
    print("=== Phase 10C-1 Real Public Readonly Shadow Once ===\n")
    os.makedirs(REPORT_DIR, exist_ok=True)

    ledger_path = os.path.join(REPORT_DIR, "phase10c_real_readonly_shadow_ledger.jsonl")
    ledger = ShadowLedger(ledger_path)

    config = DataSourceConfig(mode="snapshot", network_enabled=True)
    adapter = BinancePublicKlineAdapter(config)

    timestamp = time.time()
    records = []
    errors = []
    symbol_results = {}

    for i, sym in enumerate(symbols):
        print(f"[{i+1}/{len(symbols)}] Fetching {sym} {timeframe} limit={limit}...")
        try:
            bars = adapter.get_bars(sym, timeframe=timeframe, limit=limit)
        except Exception as e:
            errors.append({"symbol": sym, "error": str(e)})
            print(f"    ERROR: {e}")
            records.append(ShadowRecord(
                timestamp=timestamp + i,
                symbol=sym,
                timeframe=timeframe,
                priority="LOW",
                signal_type="observation",
                plan_id=f"real_obs_{sym}",
                valid_plan=False,
                reject_reason=f"fetch_error: {e}",
                entry=0.0, stop=0.0, take_profit=0.0, rr=0.0,
                outcome="ERROR", pnl=0.0, expectancy_input=0.0,
                data_quality_ok=False,
                safety_flags=SAFETY_FLAGS,
            ))
            continue

        if not bars:
            errors.append({"symbol": sym, "error": "empty_response"})
            print(f"    EMPTY response")
            records.append(ShadowRecord(
                timestamp=timestamp + i,
                symbol=sym,
                timeframe=timeframe,
                priority="LOW",
                signal_type="observation",
                plan_id=f"real_obs_{sym}",
                valid_plan=False,
                reject_reason="empty_response",
                entry=0.0, stop=0.0, take_profit=0.0, rr=0.0,
                outcome="ERROR", pnl=0.0, expectancy_input=0.0,
                data_quality_ok=False,
                safety_flags=SAFETY_FLAGS,
            ))
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
        print(f"    OK: {len(bars)} bars, quality_ok={qr.ok}, last_close={last_bar.close}")

        records.append(ShadowRecord(
            timestamp=timestamp + i,
            symbol=sym,
            timeframe=timeframe,
            priority="MEDIUM",
            signal_type="observation",
            plan_id=f"real_obs_{sym}",
            valid_plan=qr.ok,
            reject_reason="" if qr.ok else "data_quality_fail",
            entry=last_bar.close,
            stop=last_bar.close * 0.98,
            take_profit=last_bar.close * 1.04,
            rr=2.0,
            outcome="OBSERVED",
            pnl=0.0,
            expectancy_input=0.0,
            data_quality_ok=qr.ok,
            safety_flags=SAFETY_FLAGS,
        ))

        time.sleep(0.5)

    for r in records:
        ledger.append(r)

    gate_result = evaluate_shadow_gate(ledger)
    summary = ledger.summary()
    summary["gate_decision"] = gate_result.decision
    summary["gate_reasons"] = gate_result.reasons
    summary["safety_flags"] = SAFETY_FLAGS
    summary["mode"] = "real_public_http"
    summary["symbols"] = symbols
    summary["timeframe"] = timeframe
    summary["limit"] = limit
    summary["public_http"] = True
    summary["errors"] = errors
    summary["symbol_results"] = symbol_results

    json_path = os.path.join(REPORT_DIR, "phase10c_real_readonly_shadow_once.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nJSON: {json_path}")

    md_path = os.path.join(REPORT_DIR, "phase10c_real_readonly_shadow_once.md")
    with open(md_path, "w") as f:
        _write_md(f, summary, gate_result, "real_public_http", True)
    print(f"Markdown: {md_path}")

    print(f"\nGate Decision: {gate_result.decision}")
    print(f"Records: {len(records)}")
    print(f"Errors: {len(errors)}")
    print("\n=== Real Public Readonly Shadow Once Complete ===")
    return 0


def _write_md(f, summary, gate_result, mode, public_http):
    f.write("# Phase 10C-1 Real Readonly Shadow Once\n\n")
    f.write(f"**Mode:** {mode}\n")
    f.write(f"**Public HTTP:** {public_http}\n")
    f.write(f"**Symbols:** {', '.join(summary.get('symbols', []))}\n")
    f.write(f"**Timeframe:** {summary.get('timeframe', '')}\n")
    f.write(f"**Limit:** {summary.get('limit', '')}\n")
    f.write(f"**Gate Decision:** {gate_result.decision}\n\n")

    f.write("## Safety Flags\n\n")
    for flag in SAFETY_FLAGS:
        f.write(f"- {flag}\n")

    f.write("\n## Metrics\n\n")
    f.write(f"- Valid Plans: {gate_result.valid_plans}\n")
    f.write(f"- HIGH: {gate_result.high_count}\n")
    f.write(f"- MEDIUM: {gate_result.medium_count}\n")
    f.write(f"- LOW: {gate_result.low_count}\n")
    f.write(f"- Total Expectancy: {gate_result.total_expectancy}\n")
    f.write(f"- Profit Factor: {gate_result.profit_factor}\n")
    f.write(f"- Safety Violations: {gate_result.safety_violations}\n")

    if summary.get("errors"):
        f.write("\n## Errors\n\n")
        for e in summary["errors"]:
            f.write(f"- {e['symbol']}: {e['error']}\n")

    if summary.get("symbol_results"):
        f.write("\n## Symbol Results\n\n")
        for sym, info in summary["symbol_results"].items():
            f.write(f"- {sym}: {info['bars_fetched']} bars, "
                    f"quality_ok={info['quality_ok']}, "
                    f"last_close={info['last_close']}\n")

    f.write("\n## Gate Reasons\n\n")
    for reason in gate_result.reasons:
        f.write(f"- {reason}\n")

    f.write("\n## Important\n\n")
    f.write("This is a one-shot public readonly shadow smoke.\n")
    f.write("It is not the 14-day Phase 10 shadow period.\n")
    f.write("It cannot pass the full shadow gate.\n")
    f.write(f"Expected gate decision: EXTEND due to insufficient samples.\n")
    f.write(f"Actual gate decision: {gate_result.decision}\n")


def main():
    parser = argparse.ArgumentParser(description="Phase 10C-1 real readonly shadow once")
    parser.add_argument("--allow-public-http", action="store_true",
                        help="Enable real Binance public HTTP calls")
    parser.add_argument("--offline-sample", action="store_true",
                        help="Run with offline/mock data only")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated symbols")
    parser.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()

    if args.offline_sample:
        return run_offline_sample()

    if not args.allow_public_http:
        print("ERROR: Must specify --allow-public-http or --offline-sample")
        print("Default mode does NOT make real HTTP calls.")
        return 1

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    for s in symbols:
        if not s.endswith("USDT") or not all(c.isalnum() for c in s):
            print(f"ERROR: Invalid symbol: {s}")
            return 1

    return run_real_public_http(symbols, args.timeframe, args.limit)


if __name__ == "__main__":
    sys.exit(main())
