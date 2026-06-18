"""Phase 10C-3F emergency readonly watchlist — real market data + enhanced signal analysis."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.data_source import DataSourceConfig, MarketBar
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.paper_trading.market_data_quality import validate_bars
from core.paper_trading.readonly_signal_analyzer import analyze_bars, SignalResult
from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord
from core.paper_trading.shadow_gate_evaluator import evaluate_shadow_gate
from core.paper_trading.watch_trigger_planner import plan_trigger, WatchTriggerPlan

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "phase10c", "emergency")

DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "ADAUSDT", "SUIUSDT",
    "WIFUSDT", "OPUSDT", "ARBUSDT", "INJUSDT", "NEARUSDT",
    "FETUSDT", "TIAUSDT", "APTUSDT", "ORDIUSDT", "1000PEPEUSDT",
    "LTCUSDT", "BCHUSDT", "ETCUSDT", "FILUSDT", "SEIUSDT",
    "JUPUSDT", "PYTHUSDT", "ENAUSDT", "WLDUSDT", "1000BONKUSDT",
]
DEFAULT_TIMEFRAMES = ["5m", "15m", "1h"]
DEFAULT_LIMIT = 120

SAFETY_FLAGS = ["PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ACCOUNT",
                "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
                "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT"]

WATCH_STATE_ORDER = ["LONG_READY", "LONG_WATCH", "NEAR_TURN_UP",
                     "SHORT_WATCH", "WEAK_AVOID", "CHOPPY_AVOID", "DATA_REJECT"]


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
                print(f"OK → {sig.watch_state} {sig.priority} {sig.trend_bias}")
            else:
                print("ANALYSIS_FAIL")
            time.sleep(0.3)

    return results, errors


def _generate_offline_results(symbols, timeframes):
    """Generate mock signal results for offline sample."""
    results = []
    states = ["LONG_READY", "LONG_WATCH", "NEAR_TURN_UP", "SHORT_WATCH",
              "WEAK_AVOID", "CHOPPY_AVOID", "LONG_WATCH", "NEAR_TURN_UP",
              "SHORT_WATCH", "WEAK_AVOID"]
    for i, sym in enumerate(symbols):
        for tf in timeframes:
            ws = states[i % len(states)]
            results.append(SignalResult(
                symbol=sym, timeframe=tf, last_close=50000.0 + i * 100,
                trend_bias="BULLISH" if ws in ("LONG_READY", "LONG_WATCH") else
                           "BEARISH" if ws in ("SHORT_WATCH", "WEAK_AVOID") else "NEUTRAL",
                macd_state="HIST_EXPANDING_GREEN" if ws in ("LONG_READY",) else
                           "HIST_SHRINKING_RED" if ws == "NEAR_TURN_UP" else "NEUTRAL",
                rsi_state="NEUTRAL", volume_state="NORMAL",
                priority="HIGH" if ws == "LONG_READY" else "MEDIUM" if ws in ("LONG_WATCH", "NEAR_TURN_UP") else "LOW",
                entry_observation=50000.0 + i * 100,
                invalidation_level=49000.0 + i * 100,
                risk_notes="offline mock",
                reasons=["offline sample data"],
                watch_state=ws,
                setup_type="LONG_BREAKOUT" if ws == "LONG_READY" else "NO_TRADE",
                turning_score=70 if ws in ("LONG_READY", "NEAR_TURN_UP") else 30,
                weakness_score=60 if ws in ("SHORT_WATCH", "WEAK_AVOID") else 20,
                risk_score=40,
                distance_to_invalidation_pct=2.0,
                distance_to_recent_high_pct=3.0,
                distance_to_recent_low_pct=1.5,
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


def _plan_to_dict(p: WatchTriggerPlan) -> dict:
    return {
        "symbol": p.symbol, "timeframe": p.timeframe, "watch_state": p.watch_state,
        "setup_type": p.setup_type, "priority": p.priority, "last_close": p.last_close,
        "trigger_type": p.trigger_type, "trigger_condition": p.trigger_condition,
        "confirmation_condition": p.confirmation_condition,
        "invalidation_condition": p.invalidation_condition,
        "risk_note": p.risk_note, "wait_note": p.wait_note,
        "action_label": p.action_label, "shadow_record_type": p.shadow_record_type,
    }


def _write_actionable_watch(date_str, plans: list[WatchTriggerPlan]):
    """Write actionable watch JSON, MD, CSV."""
    wait_confirm = [p for p in plans if p.action_label == "WAIT_CONFIRMATION"]
    watch_now = [p for p in plans if p.action_label == "WATCH_NOW"]
    short_obs = [p for p in plans if p.action_label == "SHORT_OBSERVE"]
    avoid = [p for p in plans if p.action_label == "AVOID"]
    data_skip = [p for p in plans if p.action_label == "DATA_SKIP"]

    # JSON
    json_data = {
        "date": date_str,
        "safety_flags": SAFETY_FLAGS,
        "total_plans": len(plans),
        "watch_now": [_plan_to_dict(p) for p in watch_now],
        "wait_confirmation": [_plan_to_dict(p) for p in wait_confirm],
        "short_observe": [_plan_to_dict(p) for p in short_obs],
        "avoid_count": len(avoid),
        "data_skip_count": len(data_skip),
        "all_plans": [_plan_to_dict(p) for p in plans],
    }
    json_path = os.path.join(REPORT_DIR, f"{date_str}_actionable_watch.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"Actionable JSON: {json_path}")

    # CSV
    csv_path = os.path.join(REPORT_DIR, f"{date_str}_actionable_watch.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "timeframe", "watch_state", "action_label",
                         "trigger_type", "last_close", "turning_score", "weakness_score",
                         "trigger_condition", "confirmation_condition",
                         "invalidation_condition", "risk_note", "wait_note"])
        for p in plans:
            writer.writerow([p.symbol, p.timeframe, p.watch_state, p.action_label,
                             p.trigger_type, p.last_close,
                             "",  # turning_score from SignalResult not in plan
                             "",
                             p.trigger_condition, p.confirmation_condition,
                             p.invalidation_condition, p.risk_note, p.wait_note])
    print(f"Actionable CSV: {csv_path}")

    # Markdown
    md_path = os.path.join(REPORT_DIR, f"{date_str}_actionable_watch.md")
    with open(md_path, "w") as f:
        f.write(f"# Actionable Readonly Watch Plan — {date_str}\n\n")
        f.write("**This is a readonly observation plan. NOT a trading recommendation.**\n\n")

        # Priority 1: WATCH_NOW + WAIT_CONFIRMATION
        f.write("## Priority 1 — WAIT_CONFIRMATION\n\n")
        top_wait = sorted(wait_confirm, key=lambda p: p.last_close, reverse=True)[:10]
        for p in top_wait + watch_now:
            _write_plan_md(f, p)

        # Priority 2: SHORT_OBSERVE
        if short_obs:
            f.write("\n## Priority 2 — SHORT_OBSERVE\n\n")
            for p in short_obs[:10]:
                _write_plan_md(f, p)

        # Avoid summary
        f.write("\n## AVOID\n\n")
        f.write(f"- CHOPPY_AVOID / WEAK_AVOID: {len(avoid)} symbols — no clear setup\n")
        f.write(f"- DATA_REJECT: {len(data_skip)} — data quality issues\n")

        f.write("\n## Safety\n\n")
        f.write("Readonly observation only.\n")
        f.write("Not a trading recommendation.\n")
        f.write("Not testnet/live.\n")
        f.write("No orders placed. No accounts accessed.\n")
    print(f"Actionable Markdown: {md_path}")


def _write_plan_md(f, p: WatchTriggerPlan):
    f.write(f"### {p.symbol} ({p.timeframe}) — {p.action_label}\n\n")
    f.write(f"- **Watch State:** {p.watch_state}\n")
    f.write(f"- **Last Close:** {p.last_close}\n")
    f.write(f"- **Trigger:** {p.trigger_condition}\n")
    if p.confirmation_condition:
        f.write(f"- **Confirmation:** {p.confirmation_condition}\n")
    f.write(f"- **Invalidation:** {p.invalidation_condition}\n")
    f.write(f"- **Risk:** {p.risk_note}\n")
    f.write(f"- **Note:** {p.wait_note}\n\n")


def _sig_to_dict(r: SignalResult) -> dict:
    return {
        "symbol": r.symbol, "timeframe": r.timeframe, "priority": r.priority,
        "last_close": r.last_close, "trend_bias": r.trend_bias,
        "macd_state": r.macd_state, "rsi_state": r.rsi_state,
        "volume_state": r.volume_state, "entry_observation": r.entry_observation,
        "invalidation_level": r.invalidation_level, "risk_notes": r.risk_notes,
        "reasons": r.reasons,
        "watch_state": r.watch_state, "setup_type": r.setup_type,
        "turning_score": r.turning_score, "weakness_score": r.weakness_score,
        "risk_score": r.risk_score,
        "distance_to_invalidation_pct": r.distance_to_invalidation_pct,
        "distance_to_recent_high_pct": r.distance_to_recent_high_pct,
        "distance_to_recent_low_pct": r.distance_to_recent_low_pct,
    }


def _write_candidate_md(f, r: SignalResult):
    f.write(f"### {r.symbol} ({r.timeframe}) — {r.watch_state} / {r.priority}\n\n")
    f.write(f"- **Last Close:** {r.last_close}\n")
    f.write(f"- **Trend:** {r.trend_bias}\n")
    f.write(f"- **MACD:** {r.macd_state}\n")
    f.write(f"- **RSI:** {r.rsi_state}\n")
    f.write(f"- **Volume:** {r.volume_state}\n")
    f.write(f"- **Setup:** {r.setup_type}\n")
    f.write(f"- **Entry Observation:** {r.entry_observation}\n")
    f.write(f"- **Invalidation:** {r.invalidation_level}\n")
    f.write(f"- **Dist to Inv:** {r.distance_to_invalidation_pct}%\n")
    f.write(f"- **Dist to High:** {r.distance_to_recent_high_pct}%\n")
    f.write(f"- **Dist to Low:** {r.distance_to_recent_low_pct}%\n")
    f.write(f"- **Turning Score:** {r.turning_score}\n")
    f.write(f"- **Weakness Score:** {r.weakness_score}\n")
    f.write(f"- **Risk Score:** {r.risk_score}\n")
    f.write(f"- **Risk:** {r.risk_notes}\n")
    f.write(f"- **Reasons:** {', '.join(r.reasons)}\n\n")


def _write_reports(date_str, results, errors, mode):
    """Write JSON, MD, CSV, and shadow ledger reports."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Categorize by watch_state
    by_ws: dict[str, list[SignalResult]] = {ws: [] for ws in WATCH_STATE_ORDER}
    for r in results:
        ws = r.watch_state if r.watch_state in by_ws else "CHOPPY_AVOID"
        by_ws[ws].append(r)

    ws_counts = {ws: len(lst) for ws, lst in by_ws.items()}

    # Multi-timeframe alignment
    sym_tf_map: dict[str, list[SignalResult]] = {}
    for r in results:
        sym_tf_map.setdefault(r.symbol, []).append(r)
    mtf_alignment = {}
    for sym, sigs in sym_tf_map.items():
        states = [s.watch_state for s in sigs]
        if len(set(states)) == 1:
            mtf_alignment[sym] = states[0]
        else:
            mtf_alignment[sym] = "MIXED"

    # Top candidates
    top_turning = sorted(results, key=lambda r: r.turning_score, reverse=True)[:10]
    top_weakness = sorted(results, key=lambda r: r.weakness_score, reverse=True)[:10]
    top_long = [r for r in results if r.watch_state in ("LONG_READY", "LONG_WATCH")]
    top_long.sort(key=lambda r: r.turning_score, reverse=True)

    # JSON
    json_data = {
        "date": date_str,
        "mode": mode,
        "safety_flags": SAFETY_FLAGS,
        "total_analyzed": len(results),
        "summary_by_watch_state": ws_counts,
        "top_turning_candidates": [_sig_to_dict(r) for r in top_turning],
        "top_weakness_candidates": [_sig_to_dict(r) for r in top_weakness],
        "top_long_candidates": [_sig_to_dict(r) for r in top_long[:10]],
        "multi_timeframe_alignment": mtf_alignment,
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
        writer.writerow(["symbol", "timeframe", "watch_state", "setup_type", "priority",
                         "last_close", "trend_bias", "macd_state", "rsi_state", "volume_state",
                         "turning_score", "weakness_score", "risk_score",
                         "invalidation_level", "distance_to_invalidation_pct",
                         "distance_to_recent_high_pct", "distance_to_recent_low_pct",
                         "risk_notes", "reasons"])
        for r in results:
            writer.writerow([r.symbol, r.timeframe, r.watch_state, r.setup_type, r.priority,
                             r.last_close, r.trend_bias, r.macd_state, r.rsi_state, r.volume_state,
                             r.turning_score, r.weakness_score, r.risk_score,
                             r.invalidation_level, r.distance_to_invalidation_pct,
                             r.distance_to_recent_high_pct, r.distance_to_recent_low_pct,
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

    # Actionable watch plans
    plans = [plan_trigger(r) for r in results]
    _write_actionable_watch(date_str, plans)

    # Markdown
    md_path = os.path.join(REPORT_DIR, f"{date_str}_signal_report.md")
    with open(md_path, "w") as f:
        f.write(f"# Emergency Watchlist Report — {date_str}\n\n")
        f.write(f"**Mode:** {mode}\n")
        f.write(f"**Analyzed:** {len(results)} symbol/timeframe combinations\n")
        f.write(f"**Gate Decision:** {gate_result.decision}\n\n")

        f.write("## Safety Flags\n\n")
        for flag in SAFETY_FLAGS:
            f.write(f"- {flag}\n")

        f.write("\n## 1. Overview\n\n")
        f.write(f"| Watch State | Count |\n|---|---|\n")
        for ws in WATCH_STATE_ORDER:
            f.write(f"| {ws} | {ws_counts[ws]} |\n")

        # LONG_READY
        if by_ws["LONG_READY"]:
            f.write("\n## 2. LONG_READY — Strong Buy Candidates\n\n")
            for r in by_ws["LONG_READY"]:
                _write_candidate_md(f, r)

        # LONG_WATCH
        if by_ws["LONG_WATCH"]:
            f.write("\n## 3. LONG_WATCH — Buy Watch\n\n")
            for r in sorted(by_ws["LONG_WATCH"], key=lambda x: x.turning_score, reverse=True):
                _write_candidate_md(f, r)

        # NEAR_TURN_UP
        if by_ws["NEAR_TURN_UP"]:
            f.write("\n## 4. NEAR_TURN_UP — Approaching Turn\n\n")
            for r in sorted(by_ws["NEAR_TURN_UP"], key=lambda x: x.turning_score, reverse=True):
                _write_candidate_md(f, r)

        # SHORT_WATCH
        if by_ws["SHORT_WATCH"]:
            f.write("\n## 5. SHORT_WATCH — Bearish/Weak\n\n")
            for r in sorted(by_ws["SHORT_WATCH"], key=lambda x: x.weakness_score, reverse=True):
                _write_candidate_md(f, r)

        # WEAK_AVOID
        if by_ws["WEAK_AVOID"]:
            f.write("\n## 6. WEAK_AVOID — Do Not Touch\n\n")
            for r in sorted(by_ws["WEAK_AVOID"], key=lambda x: x.weakness_score, reverse=True):
                _write_candidate_md(f, r)

        # CHOPPY_AVOID
        if by_ws["CHOPPY_AVOID"]:
            f.write("\n## 7. CHOPPY_AVOID — Choppy/Avoid\n\n")
            for r in by_ws["CHOPPY_AVOID"]:
                _write_candidate_md(f, r)

        # DATA_REJECT
        if by_ws["DATA_REJECT"]:
            f.write("\n## 8. DATA_REJECT — Data Issues\n\n")
            for r in by_ws["DATA_REJECT"]:
                _write_candidate_md(f, r)

        # Multi-timeframe alignment
        f.write("\n## 9. Multi-Timeframe Alignment\n\n")
        f.write("| Symbol | Alignment |\n|---|---|\n")
        for sym, align in sorted(mtf_alignment.items()):
            f.write(f"| {sym} | {align} |\n")

        # Risk
        f.write("\n## 10. Risk Disclaimer\n\n")
        f.write("This is a readonly observation report.\n")
        f.write("It is NOT a trading recommendation.\n")
        f.write("It is NOT testnet or live trading.\n")
        f.write("No orders are placed. No accounts are accessed.\n")
        f.write("Always do your own research and risk management.\n")

        if errors:
            f.write("\n## Errors\n\n")
            for e in errors:
                f.write(f"- {e['symbol']} {e['timeframe']}: {e['error']}\n")
    print(f"Markdown: {md_path}")

    return gate_result, ws_counts


def run_offline(symbols, timeframes):
    print(f"=== Phase 10C-3F Emergency Watchlist (offline) ===\n")
    results, errors = _generate_offline_results(symbols, timeframes)
    date_str = _today_str()
    gate, ws_counts = _write_reports(date_str, results, errors, "offline_sample")
    print(f"\nGate: {gate.decision}")
    for ws, cnt in ws_counts.items():
        if cnt > 0:
            print(f"  {ws}: {cnt}")
    print("\n=== Offline Complete ===")
    return 0


def run_real_http(symbols, timeframes, limit):
    print(f"=== Phase 10C-3F Emergency Watchlist (real HTTP) ===\n")
    config = DataSourceConfig(mode="snapshot", network_enabled=True)
    adapter = BinancePublicKlineAdapter(config)
    results, errors = _fetch_and_analyze(adapter, symbols, timeframes, limit)
    date_str = _today_str()
    gate, ws_counts = _write_reports(date_str, results, errors, "real_public_http")
    print(f"\nGate: {gate.decision}")
    for ws, cnt in ws_counts.items():
        if cnt > 0:
            print(f"  {ws}: {cnt}")
    print(f"Errors: {len(errors)}")
    print("\n=== Real HTTP Complete ===")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 10C-3F emergency readonly watchlist")
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
