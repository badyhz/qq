"""Phase 10C-3E emergency readonly signal report — real market data + signal analysis."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.data_source import DataSourceConfig, MarketBar
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.paper_trading.market_data_quality import validate_bars
from core.paper_trading.readonly_signal_analyzer import analyze_bars, SignalResult
from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord
from core.paper_trading.shadow_gate_evaluator import evaluate_shadow_gate

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "phase10c", "emergency")

DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "ADAUSDT", "SUIUSDT",
    "WIFUSDT", "OPUSDT", "ARBUSDT", "INJUSDT", "NEARUSDT",
    "FETUSDT", "TIAUSDT", "APTUSDT", "ORDIUSDT", "1000PEPEUSDT",
]
DEFAULT_TIMEFRAMES = ["15m", "1h"]
DEFAULT_LIMIT = 120

SAFETY_FLAGS = ["PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ACCOUNT",
                "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
                "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT"]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _fetch_and_analyze(adapter, symbols, timeframes, limit):
    """Fetch klines for each symbol/timeframe and analyze signals."""
    results: list[SignalResult] = []
    errors = []
    fetch_count = 0

    total = len(symbols) * len(timeframes)
    for sym in symbols:
        for tf in timeframes:
            fetch_count += 1
            print(f"  [{fetch_count}/{total}] {sym} {tf} limit={limit}...", end=" ")
            try:
                bars = adapter.get_bars(sym, timeframe=tf, limit=limit)
            except Exception as e:
                errors.append({"symbol": sym, "timeframe": tf, "error": str(e)})
                print(f"ERROR: {e}")
                continue

            if not bars:
                errors.append({"symbol": sym, "timeframe": tf, "error": "empty_response"})
                print("EMPTY")
                continue

            qr = validate_bars(bars)
            if not qr.ok:
                errors.append({"symbol": sym, "timeframe": tf, "error": f"data_quality_fail: {qr.issues[:3]}"})
                print(f"QUALITY_FAIL ({len(qr.issues)} issues)")
                continue

            sig = analyze_bars(bars)
            if sig:
                results.append(sig)
                print(f"OK → {sig.priority} {sig.trend_bias} {sig.macd_state}")
            else:
                print("ANALYSIS_FAIL")
            time.sleep(0.3)

    return results, errors


def _generate_offline_results(symbols, timeframes):
    """Generate mock signal results for offline sample."""
    results = []
    for i, sym in enumerate(symbols):
        for tf in timeframes:
            results.append(SignalResult(
                symbol=sym, timeframe=tf, last_close=50000.0 + i * 100,
                trend_bias="BULLISH" if i % 3 == 0 else "NEUTRAL",
                macd_state="HIST_EXPANDING_GREEN" if i % 2 == 0 else "NEUTRAL",
                rsi_state="NEUTRAL", volume_state="NORMAL",
                priority="MEDIUM" if i % 3 != 2 else "LOW",
                entry_observation=50000.0 + i * 100,
                invalidation_level=49000.0 + i * 100,
                risk_notes="offline mock",
                reasons=["offline sample data"],
            ))
    return results, []


def _to_shadow_record(sig: SignalResult, ts: float) -> ShadowRecord:
    return ShadowRecord(
        timestamp=ts, symbol=sig.symbol, timeframe=sig.timeframe,
        priority=sig.priority, signal_type="readonly_signal",
        plan_id=f"signal_{sig.symbol}_{sig.timeframe}",
        valid_plan=sig.priority != "REJECT",
        reject_reason="" if sig.priority != "REJECT" else "; ".join(sig.reasons),
        entry=sig.entry_observation, stop=sig.invalidation_level,
        take_profit=sig.entry_observation * 1.04, rr=2.0,
        outcome="OBSERVED", pnl=0.0, expectancy_input=0.0,
        data_quality_ok=True, safety_flags=SAFETY_FLAGS,
    )


def _write_reports(date_str, results, errors, mode):
    """Write JSON, MD, CSV, and shadow ledger reports."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Categorize
    high = [r for r in results if r.priority == "HIGH"]
    medium = [r for r in results if r.priority == "MEDIUM"]
    low = [r for r in results if r.priority == "LOW"]
    reject = [r for r in results if r.priority == "REJECT"]

    # JSON
    json_data = {
        "date": date_str,
        "mode": mode,
        "safety_flags": SAFETY_FLAGS,
        "total_analyzed": len(results),
        "high_count": len(high),
        "medium_count": len(medium),
        "low_count": len(low),
        "reject_count": len(reject),
        "errors": errors,
        "candidates": [_sig_to_dict(r) for r in results],
    }
    json_path = os.path.join(REPORT_DIR, f"{date_str}_signal_report.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"\nJSON: {json_path}")

    # CSV
    csv_path = os.path.join(REPORT_DIR, f"{date_str}_candidates.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "timeframe", "priority", "last_close", "trend_bias",
                         "macd_state", "rsi_state", "volume_state", "invalidation_level",
                         "risk_notes", "reasons"])
        for r in results:
            writer.writerow([r.symbol, r.timeframe, r.priority, r.last_close, r.trend_bias,
                             r.macd_state, r.rsi_state, r.volume_state, r.invalidation_level,
                             r.risk_notes, "; ".join(r.reasons)])
    print(f"CSV: {csv_path}")

    # Shadow ledger
    ledger_path = os.path.join(REPORT_DIR, f"{date_str}_shadow_ledger.jsonl")
    ledger = ShadowLedger(ledger_path)
    ts = time.time()
    for i, sig in enumerate(results):
        ledger.append(_to_shadow_record(sig, ts + i))
    gate_result = evaluate_shadow_gate(ledger)
    print(f"Shadow ledger: {ledger_path}")

    # Markdown
    md_path = os.path.join(REPORT_DIR, f"{date_str}_signal_report.md")
    with open(md_path, "w") as f:
        f.write(f"# Emergency Readonly Signal Report — {date_str}\n\n")
        f.write(f"**Mode:** {mode}\n")
        f.write(f"**Analyzed:** {len(results)} symbol/timeframe combinations\n")
        f.write(f"**Gate Decision:** {gate_result.decision}\n\n")

        f.write("## Safety Flags\n\n")
        for flag in SAFETY_FLAGS:
            f.write(f"- {flag}\n")

        f.write("\n## Summary\n\n")
        f.write(f"| Priority | Count |\n|---|---|\n")
        f.write(f"| HIGH | {len(high)} |\n")
        f.write(f"| MEDIUM | {len(medium)} |\n")
        f.write(f"| LOW | {len(low)} |\n")
        f.write(f"| REJECT | {len(reject)} |\n")

        if high:
            f.write("\n## HIGH Candidates\n\n")
            for r in high:
                _write_candidate_md(f, r)

        if medium:
            f.write("\n## MEDIUM Candidates\n\n")
            for r in medium:
                _write_candidate_md(f, r)

        if low:
            f.write("\n## LOW Observations\n\n")
            for r in low:
                _write_candidate_md(f, r)

        if reject:
            f.write("\n## REJECT / Data Issues\n\n")
            for r in reject:
                _write_candidate_md(f, r)

        if errors:
            f.write("\n## Errors\n\n")
            for e in errors:
                f.write(f"- {e['symbol']} {e['timeframe']}: {e['error']}\n")

        f.write("\n## Disclaimer\n\n")
        f.write("This is a readonly observation report.\n")
        f.write("It is NOT a trading recommendation.\n")
        f.write("It is NOT testnet or live trading.\n")
        f.write("No orders are placed. No accounts are accessed.\n")
    print(f"Markdown: {md_path}")

    return gate_result


def _write_candidate_md(f, r: SignalResult):
    f.write(f"### {r.symbol} ({r.timeframe}) — {r.priority}\n\n")
    f.write(f"- **Last Close:** {r.last_close}\n")
    f.write(f"- **Trend:** {r.trend_bias}\n")
    f.write(f"- **MACD:** {r.macd_state}\n")
    f.write(f"- **RSI:** {r.rsi_state}\n")
    f.write(f"- **Volume:** {r.volume_state}\n")
    f.write(f"- **Entry Observation:** {r.entry_observation}\n")
    f.write(f"- **Invalidation:** {r.invalidation_level}\n")
    f.write(f"- **Risk:** {r.risk_notes}\n")
    f.write(f"- **Reasons:** {', '.join(r.reasons)}\n\n")


def _sig_to_dict(r: SignalResult) -> dict:
    return {
        "symbol": r.symbol, "timeframe": r.timeframe, "priority": r.priority,
        "last_close": r.last_close, "trend_bias": r.trend_bias,
        "macd_state": r.macd_state, "rsi_state": r.rsi_state,
        "volume_state": r.volume_state, "entry_observation": r.entry_observation,
        "invalidation_level": r.invalidation_level, "risk_notes": r.risk_notes,
        "reasons": r.reasons,
    }


def run_offline(symbols, timeframes):
    print(f"=== Phase 10C-3E Emergency Signal Report (offline) ===\n")
    results, errors = _generate_offline_results(symbols, timeframes)
    date_str = _today_str()
    gate = _write_reports(date_str, results, errors, "offline_sample")
    print(f"\nGate: {gate.decision}")
    print(f"HIGH: {len([r for r in results if r.priority == 'HIGH'])}")
    print(f"MEDIUM: {len([r for r in results if r.priority == 'MEDIUM'])}")
    print("\n=== Offline Complete ===")
    return 0


def run_real_http(symbols, timeframes, limit):
    print(f"=== Phase 10C-3E Emergency Signal Report (real HTTP) ===\n")
    config = DataSourceConfig(mode="snapshot", network_enabled=True)
    adapter = BinancePublicKlineAdapter(config)
    results, errors = _fetch_and_analyze(adapter, symbols, timeframes, limit)
    date_str = _today_str()
    gate = _write_reports(date_str, results, errors, "real_public_http")
    print(f"\nGate: {gate.decision}")
    print(f"HIGH: {len([r for r in results if r.priority == 'HIGH'])}")
    print(f"MEDIUM: {len([r for r in results if r.priority == 'MEDIUM'])}")
    print(f"Errors: {len(errors)}")
    print("\n=== Real HTTP Complete ===")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 10C-3E emergency readonly signal report")
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
