from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import ema, interval_ms, load_cached_klines, read_csv_rows, to_epoch_ms, to_float_nan


FIELDS = [
    "created_at",
    "candidate_id",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "source",
    "candidate_status",
    "submit_permission",
    "reason",
    "entry_price",
    "signal_time",
    "snapshot_status",
    "would_have_submitted",
    "collector_mode",
    "signal_strength_score",
    "trend_score",
    "breakout_score",
    "risk_reward_score",
    "near_miss",
    "near_miss_reason",
    "filter_fail_reasons",
    "dedupe_key",
    "is_duplicate",
    "cooldown_blocked",
    "cooldown_remaining_bars",
    "dedupe_reason",
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except OSError:
        return []
    return rows


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def _parse_csv_list(value: str) -> set[str]:
    return {item.strip().upper() for item in str(value or "").split(",") if item.strip()}


def _candidate_key(symbol: str, side: str, timeframe: str, signal_time: str) -> str:
    return f"{symbol}|{side}|{timeframe}|{signal_time}"


def _to_str_bool(value: bool) -> str:
    return "true" if bool(value) else "false"


def collect_shadow_candidates(
    *,
    watchlist_csv: str = "reports/next_trading_day_strategy_plan/strategy_watchlist.csv",
    symbol_side_csv: str = "reports/symbol_side_recommendations/symbol_side_recommendations.csv",
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    kline_cache_dir: str = "data/cache/klines",
    shadow_candidates_jsonl: str = "logs/shadow_candidates.jsonl",
    output_dir: str = "reports/shadow_candidate_collection",
    symbols: str = "",
    timeframes: str = "",
    max_candidates: int = 20,
    collector_mode: str = "strict",
    min_breakout_score: float = 60.0,
    min_trend_score: float = 60.0,
    min_risk_reward: float = 1.0,
    allow_near_miss: bool = False,
    near_miss_threshold: float = 0.8,
    dedupe_window_bars: int = 12,
    cooldown_bars: int = 12,
    dedupe_price_pct: float = 0.1,
) -> dict[str, Any]:
    mode = str(collector_mode or "strict").strip().lower()
    if mode not in {"strict", "observation", "diagnostic"}:
        mode = "strict"
    watch_rows = read_csv_rows(Path(watchlist_csv))
    symbol_side_rows = read_csv_rows(Path(symbol_side_csv))
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))
    symbol_filter = _parse_csv_list(symbols)
    timeframe_filter = {item.strip() for item in str(timeframes or "").split(",") if item.strip()}
    max_n = max(1, int(max_candidates or 20))

    symbol_side_index = {
        (
            str(row.get("symbol", "")).strip().upper(),
            str(row.get("side", "")).strip().upper(),
            str(row.get("timeframe", "5m")).strip(),
        ): row
        for row in symbol_side_rows
    }
    strategy_index = {
        str(row.get("strategy_key", "")).strip(): row
        for row in strategy_rows
        if str(row.get("strategy_key", "")).strip()
    }

    existing = _load_jsonl(Path(shadow_candidates_jsonl))
    existing_keys = {
        _candidate_key(
            str(row.get("symbol", "")).strip().upper(),
            _normalize_side(row.get("side", "")),
            str(row.get("timeframe", "5m")).strip(),
            str(row.get("signal_time", "")).strip(),
        )
        for row in existing
    }

    collected: list[dict[str, Any]] = []
    missing_klines_count = 0
    missing_kline_symbols: set[str] = set()
    missing_kline_timeframes: set[str] = set()
    symbols_with_cache: set[str] = set()
    symbols_still_missing_cache: set[str] = set()
    evaluated_count = 0
    scanned_keys: set[str] = set()
    scanned_symbols: set[str] = set()
    strict_candidate_count = 0
    near_miss_candidate_count = 0
    raw_signal_count = 0
    deduped_signal_count = 0
    duplicate_count = 0
    cooldown_blocked_count = 0
    trend_pass_count = 0
    breakout_pass_count = 0
    risk_reward_pass_count = 0
    strict_pass_count = 0
    filter_fail_summary: dict[str, int] = {
        "trend_not_aligned": 0,
        "breakout_not_confirmed": 0,
        "risk_reward_too_low": 0,
        "insufficient_bars": 0,
    }
    for row in watch_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        side = _normalize_side(row.get("side", "LONG"))
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(row.get("strategy_key", "")).strip() or f"{symbol}_{side}_{timeframe}"
        if symbol_filter and symbol not in symbol_filter:
            continue
        if timeframe_filter and timeframe not in timeframe_filter:
            continue

        allowed_action = str(row.get("allowed_action", "OBSERVE_ONLY")).strip().upper()
        submit_permission = str(row.get("submit_permission", "NO_TESTNET_SUBMIT_TODAY")).strip().upper()
        if allowed_action == "BLOCKED":
            continue

        evaluated_count += 1
        scanned_keys.add(strategy_key)
        scanned_symbols.add(symbol)
        klines = load_cached_klines(cache_root=kline_cache_dir, symbol=symbol, timeframe=timeframe)
        if len(klines) < 2:
            missing_klines_count += 1
            filter_fail_summary["insufficient_bars"] = int(filter_fail_summary.get("insufficient_bars", 0)) + 1
            if symbol:
                missing_kline_symbols.add(symbol)
                symbols_still_missing_cache.add(symbol)
            if timeframe:
                missing_kline_timeframes.add(timeframe)
            continue
        if symbol:
            symbols_with_cache.add(symbol)
        closes = [float(item.get("close", 0.0) or 0.0) for item in klines]
        opens = [float(item.get("open", 0.0) or 0.0) for item in klines]
        highs = [float(item.get("high", 0.0) or 0.0) for item in klines]
        lows = [float(item.get("low", 0.0) or 0.0) for item in klines]
        ema21 = ema(closes, 21)
        last = klines[-1]
        last_close = closes[-1]
        last_open = opens[-1]
        last_ema21 = ema21[-1] if ema21 else last_close
        prev_ema = ema21[-5] if len(ema21) >= 5 else last_ema21
        ema_slope_pct = ((last_ema21 - prev_ema) / abs(prev_ema) * 100.0) if prev_ema else 0.0
        lookback = min(20, max(2, len(highs) - 1))
        prev_high = max(highs[-(lookback + 1) : -1]) if len(highs) >= 2 else last_close
        prev_low = min(lows[-(lookback + 1) : -1]) if len(lows) >= 2 else last_close

        trend_aligned = (
            (side == "LONG" and last_close >= last_ema21 and ema_slope_pct >= 0)
            or (side == "SHORT" and last_close <= last_ema21 and ema_slope_pct <= 0)
        )
        if trend_aligned:
            trend_pass_count += 1
        trend_score = 0.0
        if side == "LONG":
            trend_score += 55.0 if last_close >= last_ema21 else 15.0
            trend_score += 45.0 if ema_slope_pct >= 0 else 15.0
        else:
            trend_score += 55.0 if last_close <= last_ema21 else 15.0
            trend_score += 45.0 if ema_slope_pct <= 0 else 15.0
        trend_score = max(0.0, min(100.0, trend_score))

        breakout_score = 0.0
        breakout_confirmed = False
        if side == "LONG":
            breakout_distance_pct = ((last_close - prev_high) / prev_high * 100.0) if prev_high > 0 else -1.0
            breakout_confirmed = breakout_distance_pct >= 0.0 and last_close >= last_open
            breakout_score = max(0.0, min(100.0, 50.0 + breakout_distance_pct * 80.0))
        else:
            breakout_distance_pct = ((prev_low - last_close) / prev_low * 100.0) if prev_low > 0 else -1.0
            breakout_confirmed = breakout_distance_pct >= 0.0 and last_close <= last_open
            breakout_score = max(0.0, min(100.0, 50.0 + breakout_distance_pct * 80.0))
        if breakout_confirmed:
            breakout_pass_count += 1

        sample_row = strategy_index.get(strategy_key, {})
        rr_value = to_float_nan(sample_row.get("risk_reward_ratio"))
        if not math.isfinite(rr_value):
            rr_value = to_float_nan(sample_row.get("planned_tp_r_multiple"))
        if not math.isfinite(rr_value):
            rr_value = 1.0
        risk_reward_score = max(0.0, min(100.0, (rr_value / max(0.01, float(min_risk_reward))) * 100.0))
        risk_reward_ok = bool(rr_value >= float(min_risk_reward))
        if risk_reward_ok:
            risk_reward_pass_count += 1

        strict_pass = bool(
            trend_score >= float(min_trend_score)
            and breakout_score >= float(min_breakout_score)
            and risk_reward_ok
            and trend_aligned
            and breakout_confirmed
        )
        if strict_pass:
            strict_pass_count += 1
        signal_strength_score = (trend_score + breakout_score + risk_reward_score) / 3.0
        threshold_score = max(0.0, min(100.0, float(near_miss_threshold) * 100.0))
        near_miss = bool((not strict_pass) and bool(allow_near_miss) and signal_strength_score >= threshold_score)
        if near_miss:
            near_miss_candidate_count += 1

        fail_reasons: list[str] = []
        if trend_score < float(min_trend_score) or (not trend_aligned):
            fail_reasons.append("trend_not_aligned")
            filter_fail_summary["trend_not_aligned"] = int(filter_fail_summary.get("trend_not_aligned", 0)) + 1
        if breakout_score < float(min_breakout_score) or (not breakout_confirmed):
            fail_reasons.append("breakout_not_confirmed")
            filter_fail_summary["breakout_not_confirmed"] = int(filter_fail_summary.get("breakout_not_confirmed", 0)) + 1
        if not risk_reward_ok:
            fail_reasons.append("risk_reward_too_low")
            filter_fail_summary["risk_reward_too_low"] = int(filter_fail_summary.get("risk_reward_too_low", 0)) + 1

        if not strict_pass and not (mode == "observation" and near_miss):
            continue
        raw_signal_count += 1

        signal_ms = int(last.get("close_time_ms", 0) or 0)
        signal_time = datetime.fromtimestamp(signal_ms / 1000.0, tz=timezone.utc).isoformat() if signal_ms > 0 else datetime.now(timezone.utc).isoformat()
        dedupe_key = _candidate_key(symbol, side, timeframe, signal_time)
        if dedupe_key in existing_keys:
            duplicate_count += 1
            continue
        window_ms = max(1, int(dedupe_window_bars or 12)) * interval_ms(timeframe)
        cooldown_ms = max(1, int(cooldown_bars or 12)) * interval_ms(timeframe)
        current_price = round(last_close, 8)
        is_duplicate = False
        duplicate_reason = ""
        cooldown_blocked = False
        cooldown_remaining_bars = 0
        latest_same_key_ms = 0
        for old in existing:
            old_symbol = str(old.get("symbol", "")).strip().upper()
            old_side = _normalize_side(old.get("side", ""))
            old_tf = str(old.get("timeframe", "5m")).strip() or "5m"
            old_key = str(old.get("strategy_key", "")).strip()
            old_ms = to_epoch_ms(old.get("signal_time"))
            if old_key == strategy_key and old_ms > latest_same_key_ms:
                latest_same_key_ms = old_ms
            if old_symbol != symbol or old_side != side or old_tf != timeframe:
                continue
            if old_ms <= 0 or signal_ms <= 0:
                continue
            if abs(signal_ms - old_ms) > window_ms:
                continue
            old_price = to_float_nan(old.get("entry_price"))
            if math.isfinite(old_price) and current_price > 0:
                price_diff_pct = abs(old_price - current_price) / current_price * 100.0
                if price_diff_pct <= float(dedupe_price_pct):
                    is_duplicate = True
                    duplicate_reason = "same_symbol_side_timeframe_within_window_and_price"
                    break
            else:
                is_duplicate = True
                duplicate_reason = "same_symbol_side_timeframe_within_window"
                break
        if is_duplicate:
            duplicate_count += 1
            continue
        if latest_same_key_ms > 0 and signal_ms > 0 and (signal_ms - latest_same_key_ms) < cooldown_ms:
            cooldown_blocked = True
            remaining_ms = max(0, cooldown_ms - (signal_ms - latest_same_key_ms))
            cooldown_remaining_bars = int(math.ceil(remaining_ms / max(1, interval_ms(timeframe))))
        if cooldown_blocked:
            cooldown_blocked_count += 1
            continue
        deduped_signal_count += 1
        existing_keys.add(dedupe_key)

        confidence = str(sample_row.get("sample_confidence_level", "UNKNOWN")).strip().upper()
        reasons = ["collect_more_samples"]
        if confidence in {"TOO_SMALL", "LOW", "UNKNOWN"}:
            reasons.append("low_sample")
        if submit_permission in {"NO_TESTNET_SUBMIT_TODAY", "NO_REAL_SUBMIT"}:
            reasons.append("no_submit")
        if near_miss:
            reasons.append("near_miss")
        candidate_status = "SHADOW_ONLY"
        if mode == "observation" and near_miss and (not strict_pass):
            candidate_status = "SHADOW_OBSERVATION_ONLY"
        if strict_pass:
            strict_candidate_count += 1
        cid_seed = f"{symbol}|{side}|{timeframe}|{signal_time}|{current_price:.8f}"
        cid_hash = hashlib.sha1(cid_seed.encode("utf-8")).hexdigest()[:8]
        candidate_id = f"shadow_{symbol}_{side}_{timeframe}_{signal_ms}_{cid_hash}"
        candidate = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "candidate_id": candidate_id,
            "symbol": symbol,
            "side": side,
            "timeframe": timeframe,
            "strategy_key": strategy_key,
            "source": "shadow_collector",
            "candidate_status": candidate_status,
            "submit_permission": "NO_SUBMIT",
            "reason": sorted(set(reasons)),
            "entry_price": round(last_close, 8),
            "signal_time": signal_time,
            "snapshot_status": "OK",
            "would_have_submitted": False,
            "collector_mode": mode,
            "signal_strength_score": round(signal_strength_score, 8),
            "trend_score": round(trend_score, 8),
            "breakout_score": round(breakout_score, 8),
            "risk_reward_score": round(risk_reward_score, 8),
            "near_miss": near_miss,
            "near_miss_reason": ";".join(fail_reasons) if near_miss else "",
            "filter_fail_reasons": ";".join(fail_reasons),
            "dedupe_key": dedupe_key,
            "is_duplicate": is_duplicate,
            "cooldown_blocked": cooldown_blocked,
            "cooldown_remaining_bars": cooldown_remaining_bars,
            "dedupe_reason": duplicate_reason,
        }
        if mode != "diagnostic":
            collected.append(candidate)
            existing.append(candidate)
        if len(collected) >= max_n:
            break

    if mode != "diagnostic":
        _append_jsonl(Path(shadow_candidates_jsonl), collected)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "shadow_candidates.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in collected:
            payload = dict(row)
            payload["reason"] = ";".join(list(row.get("reason", []))) if isinstance(row.get("reason", []), list) else str(row.get("reason", ""))
            writer.writerow({field: payload.get(field, "") for field in FIELDS})

    final_verdict = "PASS"
    status_reason = "collected_shadow_candidates"
    if mode == "diagnostic":
        status_reason = "diagnostic_only"
    elif not collected:
        status_reason = "no_new_shadow_candidates"
        if missing_klines_count > 0 and evaluated_count == missing_klines_count:
            status_reason = "missing_klines"

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluated_watchlist_count": evaluated_count,
        "collected_count": len(collected),
        "missing_klines_count": missing_klines_count,
        "status_reason": status_reason,
        "final_verdict": final_verdict,
        "collector_mode": mode,
        "shadow_candidates_jsonl": shadow_candidates_jsonl,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "missing_kline_symbols": sorted(missing_kline_symbols),
        "missing_kline_timeframes": sorted(missing_kline_timeframes),
        "kline_cache_checked": bool(evaluated_count > 0),
        "symbols_with_cache": sorted(symbols_with_cache),
        "symbols_still_missing_cache": sorted(symbols_still_missing_cache),
        "cache_recovered": bool(len(symbols_with_cache) > 0),
        "missing_klines_resolved": bool(status_reason != "missing_klines"),
        "scanned_symbol_count": len(scanned_symbols),
        "scanned_strategy_count": len(scanned_keys),
        "strict_candidate_count": strict_candidate_count,
        "near_miss_candidate_count": near_miss_candidate_count,
        "raw_signal_count": raw_signal_count,
        "deduped_signal_count": deduped_signal_count,
        "duplicate_count": duplicate_count,
        "cooldown_blocked_count": cooldown_blocked_count,
        "trend_pass_count": trend_pass_count,
        "breakout_pass_count": breakout_pass_count,
        "risk_reward_pass_count": risk_reward_pass_count,
        "strict_pass_count": strict_pass_count,
        "filter_fail_summary": filter_fail_summary,
    }
    if status_reason == "missing_klines":
        summary["recommended_next_action"] = "RUN_KLINE_BACKFILL"
        summary["recommended_commands"] = [
            "PYTHONPATH=. ./.venv/bin/python scripts/generate_kline_cache_backfill_plan.py --json",
            "PYTHONPATH=. ./.venv/bin/python scripts/run_public_kline_backfill.py --dry-run --public-only --json",
        ]
    else:
        summary["recommended_next_action"] = "COLLECT_SHADOW_CANDIDATES"
        summary["recommended_commands"] = []
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Candidate Collection",
        "",
        f"- final_verdict: {final_verdict}",
        f"- collector_mode: {mode}",
        f"- evaluated_watchlist_count: {evaluated_count}",
        f"- collected_count: {len(collected)}",
        f"- missing_klines_count: {missing_klines_count}",
        f"- status_reason: {status_reason}",
        f"- strict_candidate_count: {strict_candidate_count}",
        f"- near_miss_candidate_count: {near_miss_candidate_count}",
        f"- duplicate_count: {duplicate_count}",
        f"- cooldown_blocked_count: {cooldown_blocked_count}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect shadow-only candidates without submit actions")
    parser.add_argument("--watchlist-csv", default="reports/next_trading_day_strategy_plan/strategy_watchlist.csv")
    parser.add_argument("--symbol-side-csv", default="reports/symbol_side_recommendations/symbol_side_recommendations.csv")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--kline-cache-dir", default="data/cache/klines")
    parser.add_argument("--shadow-candidates-jsonl", default="logs/shadow_candidates.jsonl")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--output-dir", default="reports/shadow_candidate_collection")
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframes", default="")
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--collector-mode", default="strict", choices=["strict", "observation", "diagnostic"])
    parser.add_argument("--min-breakout-score", type=float, default=60.0)
    parser.add_argument("--min-trend-score", type=float, default=60.0)
    parser.add_argument("--min-risk-reward", type=float, default=1.0)
    parser.add_argument("--allow-near-miss", action="store_true")
    parser.add_argument("--near-miss-threshold", type=float, default=0.8)
    parser.add_argument("--dedupe-window-bars", type=int, default=12)
    parser.add_argument("--cooldown-bars", type=int, default=12)
    parser.add_argument("--dedupe-price-pct", type=float, default=0.1)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    shadow_jsonl = str(args.shadow_candidates_jsonl or "")
    if not shadow_jsonl:
        shadow_jsonl = str(Path(str(args.logs_dir or "logs")) / "shadow_candidates.jsonl")
    result = collect_shadow_candidates(
        watchlist_csv=str(args.watchlist_csv or Path(str(args.reports_dir or "reports")) / "next_trading_day_strategy_plan" / "strategy_watchlist.csv"),
        symbol_side_csv=str(args.symbol_side_csv or Path(str(args.reports_dir or "reports")) / "symbol_side_recommendations" / "symbol_side_recommendations.csv"),
        strategy_candidate_csv=str(args.strategy_candidate_csv or Path(str(args.reports_dir or "reports")) / "strategy_candidate_score" / "strategy_candidate_score.csv"),
        kline_cache_dir=str(args.kline_cache_dir or "data/cache/klines"),
        shadow_candidates_jsonl=shadow_jsonl,
        output_dir=str(args.output_dir or "reports/shadow_candidate_collection"),
        symbols=str(args.symbols or ""),
        timeframes=str(args.timeframes or ""),
        max_candidates=int(args.max_candidates or 20),
        collector_mode=str(args.collector_mode or "strict"),
        min_breakout_score=float(args.min_breakout_score if args.min_breakout_score is not None else 60.0),
        min_trend_score=float(args.min_trend_score if args.min_trend_score is not None else 60.0),
        min_risk_reward=float(args.min_risk_reward if args.min_risk_reward is not None else 1.0),
        allow_near_miss=bool(args.allow_near_miss),
        near_miss_threshold=float(args.near_miss_threshold if args.near_miss_threshold is not None else 0.8),
        dedupe_window_bars=int(args.dedupe_window_bars if args.dedupe_window_bars is not None else 12),
        cooldown_bars=int(args.cooldown_bars if args.cooldown_bars is not None else 12),
        dedupe_price_pct=float(args.dedupe_price_pct if args.dedupe_price_pct is not None else 0.1),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"collected_count={result.get('collected_count', 0)}")
    print(f"status_reason={result.get('status_reason', '')}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
