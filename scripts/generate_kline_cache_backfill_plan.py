from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "rank",
    "symbol",
    "timeframe",
    "strategy_key",
    "required_bars",
    "lookback_days",
    "cache_status",
    "missing_reason",
    "backfill_priority",
    "backfill_mode",
    "public_endpoint_type",
    "universe_source",
    "liquidity_tier",
    "cache_file_exists",
    "cache_bar_count",
    "cache_last_open_time",
    "cache_age_minutes",
    "reason",
    "next_action",
]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_cached_bar_count(cache_dir: Path, symbol: str, timeframe: str) -> tuple[int, int, int]:
    root = cache_dir / symbol / timeframe
    if not root.exists():
        return 0, 0, 0
    bars = 0
    files = 0
    last_open_ms = 0
    for path in sorted(root.glob("*.csv")):
        files += 1
        rows = read_csv_rows(path)
        bars += len(rows)
        for row in rows:
            value = to_float_nan(row.get("open_time_ms", ""))
            if value == value:
                last_open_ms = max(last_open_ms, int(value))
    return bars, files, last_open_ms


def _liquidity_tier(symbol: str) -> str:
    sym = str(symbol or "").strip().upper()
    if sym in {"BTCUSDT", "ETHUSDT"}:
        return "TIER1"
    if sym in {"SOLUSDT", "BNBUSDT"}:
        return "TIER2"
    if sym in {"OPUSDT", "FETUSDT"}:
        return "TIER3"
    return "OTHER"


def _to_iso(ms: int) -> str:
    if ms <= 0:
        return ""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat()


def generate_kline_cache_backfill_plan(
    *,
    shadow_scan_plan_csv: str = "reports/shadow_scan_plan/shadow_scan_plan.csv",
    shadow_scan_universe_csv: str = "reports/shadow_scan_universe/shadow_scan_universe.csv",
    collect_more_samples_plan_csv: str = "reports/collect_more_samples_plan/collect_more_samples_plan.csv",
    sample_tracker_csv: str = "reports/sample_collection_tracker/sample_collection_tracker.csv",
    shadow_collection_summary_json: str = "reports/shadow_candidate_collection/summary.json",
    shadow_outcomes_summary_json: str = "reports/shadow_candidate_outcomes/summary.json",
    cache_dir: str = "data/cache/klines",
    output_dir: str = "reports/kline_cache_backfill_plan",
) -> dict[str, Any]:
    scan_rows = read_csv_rows(Path(shadow_scan_plan_csv))
    universe_rows = read_csv_rows(Path(shadow_scan_universe_csv))
    collect_rows = read_csv_rows(Path(collect_more_samples_plan_csv))
    tracker_rows = read_csv_rows(Path(sample_tracker_csv))
    shadow_collection_summary = _load_json(Path(shadow_collection_summary_json))
    shadow_outcome_summary = _load_json(Path(shadow_outcomes_summary_json))
    cache_root = Path(cache_dir)

    tracker_index = {
        str(row.get("strategy_key", "")).strip(): row
        for row in tracker_rows
        if str(row.get("strategy_key", "")).strip()
    }
    collect_index = {
        str(row.get("strategy_key", "")).strip(): row
        for row in collect_rows
        if str(row.get("strategy_key", "")).strip()
    }

    candidates: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in universe_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(row.get("strategy_key", "")).strip() or f"{symbol}_LONG_{timeframe}"
        if not symbol:
            continue
        key = (symbol, timeframe, strategy_key)
        candidates[key] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy_key": strategy_key,
            "scan_priority": str(row.get("scan_priority", "P2")).strip().upper() or "P2",
            "required_next_samples": int(to_float_nan(row.get("required_next_samples")) if str(row.get("required_next_samples", "")).strip() else 0),
            "universe_source": "shadow_scan_universe",
        }
    for row in scan_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(row.get("strategy_key", "")).strip() or f"{symbol}_LONG_{timeframe}"
        if not symbol:
            continue
        key = (symbol, timeframe, strategy_key)
        candidates[key] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy_key": strategy_key,
            "scan_priority": str(row.get("scan_priority", "P2")).strip().upper() or "P2",
            "required_next_samples": int(to_float_nan(row.get("required_next_samples")) if str(row.get("required_next_samples", "")).strip() else 0),
            "universe_source": "shadow_scan_plan",
        }
    for row in collect_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(row.get("strategy_key", "")).strip() or f"{symbol}_LONG_{timeframe}"
        if not symbol:
            continue
        key = (symbol, timeframe, strategy_key)
        current = candidates.get(
            key,
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "strategy_key": strategy_key,
                "scan_priority": "P2",
                "required_next_samples": 0,
                "universe_source": "collect_more_samples_plan",
            },
        )
        current["collection_priority"] = str(row.get("collection_priority", "P2")).strip().upper() or "P2"
        current["required_next_samples"] = max(
            int(current.get("required_next_samples", 0)),
            int(to_float_nan(row.get("required_next_samples")) if str(row.get("required_next_samples", "")).strip() else 0),
        )
        candidates[key] = current

    missing_klines_signal = (
        str(shadow_collection_summary.get("status_reason", "")).strip().lower() == "missing_klines"
        or str(shadow_outcome_summary.get("reason", "")).strip().lower() in {"missing_klines", "no_shadow_candidates"}
    )

    rows: list[dict[str, Any]] = []
    for rank, key in enumerate(sorted(candidates.keys()), start=1):
        item = candidates[key]
        symbol = str(item["symbol"])
        timeframe = str(item["timeframe"])
        strategy_key = str(item["strategy_key"])
        tracker = tracker_index.get(strategy_key, {})
        required_next_samples = int(item.get("required_next_samples", 0))
        bars_per_sample = 24
        required_bars = max(300, min(3000, (required_next_samples if required_next_samples > 0 else 20) * bars_per_sample))
        lookback_days = max(3, min(30, int(required_bars / 288) + 1))
        cached_bars, cache_files, cache_last_open_ms = _read_cached_bar_count(cache_root, symbol, timeframe)

        cache_status = "UNKNOWN"
        missing_reason = "cache_unknown"
        if cache_files <= 0 or cached_bars <= 0:
            cache_status = "MISSING"
            missing_reason = "no_cache_files"
        elif cached_bars < required_bars:
            cache_status = "PARTIAL"
            missing_reason = "insufficient_cached_bars"
        else:
            cache_status = "OK"
            missing_reason = "enough_cached_bars"

        backfill_priority = "P3"
        collection_priority = str(item.get("collection_priority", "")).strip().upper()
        scan_priority = str(item.get("scan_priority", "P2")).strip().upper()
        collection_status = str(tracker.get("collection_status", "")).strip().upper()
        liquidity_tier = _liquidity_tier(symbol)
        is_low_sample_focus = (
            collection_priority == "P0"
            or "low_sample" in str(item.get("reason", "")).lower()
            or collection_status in {"LOW_CONFIDENCE", "COLLECTING"}
        )
        if cache_status in {"MISSING", "PARTIAL"} and is_low_sample_focus:
            backfill_priority = "P0"
        elif cache_status in {"MISSING", "PARTIAL"} and liquidity_tier in {"TIER1", "TIER2", "TIER3"} and timeframe == "5m":
            backfill_priority = "P1"
        elif cache_status in {"MISSING", "PARTIAL"} and liquidity_tier in {"TIER1", "TIER2", "TIER3"} and timeframe == "15m":
            backfill_priority = "P2"
        elif cache_status in {"MISSING", "PARTIAL"} and scan_priority in {"P0", "P1"}:
            backfill_priority = "P2"
        else:
            backfill_priority = "P3"

        reason_parts = [missing_reason]
        if missing_klines_signal:
            reason_parts.append("shadow_pipeline_missing_klines")
        if required_next_samples > 0:
            reason_parts.append("collect_more_samples")
        next_action = "no_backfill_needed" if cache_status == "OK" else "run_public_kline_backfill"

        cache_age_minutes = (
            int((datetime.now(timezone.utc).timestamp() * 1000 - cache_last_open_ms) / 60000) if cache_last_open_ms > 0 else -1
        )
        universe_source = str(item.get("universe_source", "shadow_scan_plan")).strip() or "shadow_scan_plan"
        rows.append(
            {
                "rank": rank,
                "symbol": symbol,
                "timeframe": timeframe,
                "strategy_key": strategy_key,
                "required_bars": required_bars,
                "lookback_days": lookback_days,
                "cache_status": cache_status,
                "missing_reason": missing_reason,
                "backfill_priority": backfill_priority,
                "backfill_mode": "PUBLIC_ONLY",
                "public_endpoint_type": "FUTURES_KLINES",
                "universe_source": universe_source,
                "liquidity_tier": liquidity_tier,
                "cache_file_exists": bool(cache_files > 0),
                "cache_bar_count": cached_bars,
                "cache_last_open_time": _to_iso(cache_last_open_ms),
                "cache_age_minutes": cache_age_minutes,
                "reason": ";".join(sorted(set(reason_parts))),
                "next_action": next_action,
            }
        )

    rows.sort(
        key=lambda row: (
            str(row.get("backfill_priority", "P9")).strip().upper(),
            -int(row.get("required_bars", 0) or 0),
            str(row.get("symbol", "")),
            str(row.get("timeframe", "")),
        )
    )
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "kline_cache_backfill_plan.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if rows else "PARTIAL",
        "total_rows": len(rows),
        "p0_count": sum(1 for row in rows if str(row.get("backfill_priority", "")).upper() == "P0"),
        "p1_count": sum(1 for row in rows if str(row.get("backfill_priority", "")).upper() == "P1"),
        "p2_count": sum(1 for row in rows if str(row.get("backfill_priority", "")).upper() == "P2"),
        "missing_or_partial_count": sum(1 for row in rows if str(row.get("cache_status", "")).upper() in {"MISSING", "PARTIAL"}),
        "cache_ok_count": sum(1 for row in rows if str(row.get("cache_status", "")).upper() == "OK"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Kline Cache Backfill Plan",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- p0_count: {summary['p0_count']}",
        f"- missing_or_partial_count: {summary['missing_or_partial_count']}",
        f"- cache_ok_count: {summary['cache_ok_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate kline cache backfill plan for shadow sample pipeline")
    parser.add_argument("--shadow-scan-plan-csv", default="reports/shadow_scan_plan/shadow_scan_plan.csv")
    parser.add_argument("--shadow-scan-universe-csv", default="reports/shadow_scan_universe/shadow_scan_universe.csv")
    parser.add_argument("--collect-more-samples-plan-csv", default="reports/collect_more_samples_plan/collect_more_samples_plan.csv")
    parser.add_argument("--sample-tracker-csv", default="reports/sample_collection_tracker/sample_collection_tracker.csv")
    parser.add_argument("--shadow-collection-summary-json", default="reports/shadow_candidate_collection/summary.json")
    parser.add_argument("--shadow-outcomes-summary-json", default="reports/shadow_candidate_outcomes/summary.json")
    parser.add_argument("--cache-dir", default="data/cache/klines")
    parser.add_argument("--output-dir", default="reports/kline_cache_backfill_plan")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_kline_cache_backfill_plan(
        shadow_scan_plan_csv=str(args.shadow_scan_plan_csv or "reports/shadow_scan_plan/shadow_scan_plan.csv"),
        shadow_scan_universe_csv=str(args.shadow_scan_universe_csv or "reports/shadow_scan_universe/shadow_scan_universe.csv"),
        collect_more_samples_plan_csv=str(args.collect_more_samples_plan_csv or "reports/collect_more_samples_plan/collect_more_samples_plan.csv"),
        sample_tracker_csv=str(args.sample_tracker_csv or "reports/sample_collection_tracker/sample_collection_tracker.csv"),
        shadow_collection_summary_json=str(args.shadow_collection_summary_json or "reports/shadow_candidate_collection/summary.json"),
        shadow_outcomes_summary_json=str(args.shadow_outcomes_summary_json or "reports/shadow_candidate_outcomes/summary.json"),
        cache_dir=str(args.cache_dir or "data/cache/klines"),
        output_dir=str(args.output_dir or "reports/kline_cache_backfill_plan"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"p0_count={result.get('p0_count', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
