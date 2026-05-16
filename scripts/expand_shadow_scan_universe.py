from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows


FIELDS = [
    "rank",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "source",
    "scan_priority",
    "allowed_collection_mode",
    "max_shadow_candidates_per_day",
    "needs_kline_cache",
    "cache_status",
    "reason",
]


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _priority_rank(value: str) -> int:
    text = str(value or "").strip().upper()
    table = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    return table.get(text, 9)


def _cache_status(cache_root: str, symbol: str, timeframe: str) -> str:
    root = Path(cache_root) / str(symbol or "").strip().upper() / str(timeframe or "5m").strip()
    if not root.exists():
        return "MISSING"
    csv_files = list(root.glob("*.csv"))
    if not csv_files:
        return "MISSING"
    return "OK"


def expand_shadow_scan_universe(
    *,
    shadow_scan_plan_csv: str = "reports/shadow_scan_plan/shadow_scan_plan.csv",
    symbol_side_csv: str = "reports/symbol_side_recommendations/symbol_side_recommendations.csv",
    collect_more_samples_plan_csv: str = "reports/collect_more_samples_plan/collect_more_samples_plan.csv",
    cache_dir: str = "data/cache/klines",
    output_dir: str = "reports/shadow_scan_universe",
    symbols: str = "OPUSDT,FETUSDT,SOLUSDT,ETHUSDT,BTCUSDT,BNBUSDT",
    timeframes: str = "5m,15m",
    max_universe_size: int = 20,
) -> dict[str, Any]:
    scan_rows = read_csv_rows(Path(shadow_scan_plan_csv))
    symbol_side_rows = read_csv_rows(Path(symbol_side_csv))
    collect_rows = read_csv_rows(Path(collect_more_samples_plan_csv))
    symbol_seed = [item.strip().upper() for item in _parse_list(symbols)]
    timeframe_seed = _parse_list(timeframes) or ["5m"]
    max_size = max(1, int(max_universe_size or 20))

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def push(item: dict[str, Any]) -> None:
        key = f"{item['symbol']}|{item['side']}|{item['timeframe']}|{item['strategy_key']}"
        if key in seen:
            return
        seen.add(key)
        candidates.append(item)

    for row in sorted(collect_rows, key=lambda r: (_priority_rank(r.get("collection_priority", "P3")), str(r.get("strategy_key", "")))):
        symbol = str(row.get("symbol", "")).strip().upper()
        side = _normalize_side(row.get("side", "LONG"))
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(row.get("strategy_key", "")).strip() or f"{symbol}_{side}_{timeframe}"
        push(
            {
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "strategy_key": strategy_key,
                "source": "collect_more_samples_plan",
                "scan_priority": str(row.get("collection_priority", "P1")).strip().upper() or "P1",
                "allowed_collection_mode": "SHADOW_ONLY",
                "max_shadow_candidates_per_day": 10,
                "needs_kline_cache": True,
                "cache_status": _cache_status(cache_dir, symbol, timeframe),
                "reason": str(row.get("reason", "collect_more_samples")).strip() or "collect_more_samples",
            }
        )

    for row in scan_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        side = _normalize_side(row.get("side", "LONG"))
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(row.get("strategy_key", "")).strip() or f"{symbol}_{side}_{timeframe}"
        mode = str(row.get("allowed_collection_mode", "")).strip().upper()
        if mode not in {"SHADOW_ONLY", "DRY_RUN_ONLY"}:
            mode = "SHADOW_ONLY"
        push(
            {
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "strategy_key": strategy_key,
                "source": "shadow_scan_plan",
                "scan_priority": str(row.get("scan_priority", "P2")).strip().upper() or "P2",
                "allowed_collection_mode": mode,
                "max_shadow_candidates_per_day": int(float(row.get("max_shadow_candidates_per_day", 10) or 10)),
                "needs_kline_cache": True,
                "cache_status": _cache_status(cache_dir, symbol, timeframe),
                "reason": str(row.get("reason", "watchlist_seed")).strip() or "watchlist_seed",
            }
        )

    side_hints: dict[str, list[str]] = {}
    for row in symbol_side_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        side = _normalize_side(row.get("side", "LONG"))
        side_hints.setdefault(symbol, [])
        if side not in side_hints[symbol]:
            side_hints[symbol].append(side)

    for symbol in symbol_seed:
        sides = side_hints.get(symbol) or ["LONG"]
        for side in sides:
            for timeframe in timeframe_seed:
                strategy_key = f"{symbol}_{side}_{timeframe}"
                push(
                    {
                        "symbol": symbol,
                        "side": side,
                        "timeframe": timeframe,
                        "strategy_key": strategy_key,
                        "source": "symbol_seed",
                        "scan_priority": "P2",
                        "allowed_collection_mode": "SHADOW_ONLY",
                        "max_shadow_candidates_per_day": 8,
                        "needs_kline_cache": True,
                        "cache_status": _cache_status(cache_dir, symbol, timeframe),
                        "reason": "expanded_scan_universe",
                    }
                )

    candidates.sort(key=lambda item: (_priority_rank(item.get("scan_priority", "P9")), item.get("symbol", ""), item.get("timeframe", "")))
    selected = candidates[:max_size]
    for idx, row in enumerate(selected, start=1):
        row["rank"] = idx

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "shadow_scan_universe.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in selected:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS",
        "total_rows": len(selected),
        "source_rows": {
            "collect_more_samples_plan": len(collect_rows),
            "shadow_scan_plan": len(scan_rows),
            "symbol_side_recommendations": len(symbol_side_rows),
        },
        "shadow_only_count": sum(1 for row in selected if str(row.get("allowed_collection_mode", "")).upper() == "SHADOW_ONLY"),
        "dry_run_only_count": sum(1 for row in selected if str(row.get("allowed_collection_mode", "")).upper() == "DRY_RUN_ONLY"),
        "missing_cache_count": sum(1 for row in selected if str(row.get("cache_status", "")).upper() != "OK"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    if len(selected) == 0:
        summary["final_verdict"] = "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Scan Universe",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- shadow_only_count: {summary['shadow_only_count']}",
        f"- dry_run_only_count: {summary['dry_run_only_count']}",
        f"- missing_cache_count: {summary['missing_cache_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Expand multi-symbol multi-timeframe shadow scan universe")
    parser.add_argument("--shadow-scan-plan-csv", default="reports/shadow_scan_plan/shadow_scan_plan.csv")
    parser.add_argument("--symbol-side-csv", default="reports/symbol_side_recommendations/symbol_side_recommendations.csv")
    parser.add_argument("--collect-more-samples-plan-csv", default="reports/collect_more_samples_plan/collect_more_samples_plan.csv")
    parser.add_argument("--cache-dir", default="data/cache/klines")
    parser.add_argument("--output-dir", default="reports/shadow_scan_universe")
    parser.add_argument("--symbols", default="OPUSDT,FETUSDT,SOLUSDT,ETHUSDT,BTCUSDT,BNBUSDT")
    parser.add_argument("--timeframes", default="5m,15m")
    parser.add_argument("--max-universe-size", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = expand_shadow_scan_universe(
        shadow_scan_plan_csv=str(args.shadow_scan_plan_csv or "reports/shadow_scan_plan/shadow_scan_plan.csv"),
        symbol_side_csv=str(args.symbol_side_csv or "reports/symbol_side_recommendations/symbol_side_recommendations.csv"),
        collect_more_samples_plan_csv=str(args.collect_more_samples_plan_csv or "reports/collect_more_samples_plan/collect_more_samples_plan.csv"),
        cache_dir=str(args.cache_dir or "data/cache/klines"),
        output_dir=str(args.output_dir or "reports/shadow_scan_universe"),
        symbols=str(args.symbols or ""),
        timeframes=str(args.timeframes or ""),
        max_universe_size=int(args.max_universe_size or 20),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"total_rows={result.get('total_rows', 0)}")


if __name__ == "__main__":
    main()
