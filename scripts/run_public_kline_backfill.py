from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from scripts.public_kline_backfill_common import (
    build_kline_request_windows,
    normalize_kline_backfill_config,
    summarize_backfill_plan,
)
from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "symbol",
    "timeframe",
    "market",
    "requested_bars",
    "fetched_bars",
    "written_bars",
    "cache_file",
    "first_open_time",
    "last_open_time",
    "coverage_status",
    "dry_run",
    "error",
]


def _to_iso(ms: int) -> str:
    if ms <= 0:
        return ""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat()


def _interval_ms(tf: str) -> int:
    text = str(tf or "5m").strip().lower()
    if not text:
        return 5 * 60_000
    unit = text[-1]
    try:
        n = max(1, int(float(text[:-1])))
    except ValueError:
        n = 5
    if unit == "m":
        return n * 60_000
    if unit == "h":
        return n * 60 * 60_000
    if unit == "d":
        return n * 24 * 60 * 60_000
    return 5 * 60_000


def _fetch_public_klines(
    *,
    symbol: str,
    timeframe: str,
    limit: int,
    market: str,
    timeout_sec: float = 12.0,
) -> dict[str, Any]:
    resolved_market = str(market or "futures").strip().lower()
    base_url = "https://fapi.binance.com" if resolved_market == "futures" else "https://api.binance.com"
    path = "/fapi/v1/klines" if resolved_market == "futures" else "/api/v3/klines"
    query = urlencode(
        {
            "symbol": str(symbol or "").strip().upper(),
            "interval": str(timeframe or "5m").strip(),
            "limit": str(max(1, min(1500, int(limit or 300)))),
        }
    )
    url = f"{base_url}{path}?{query}"
    try:
        with urlopen(url, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        return {"ok": False, "error": f"http_{exc.code}"}
    except URLError as exc:
        return {"ok": False, "error": f"url_error:{exc.reason}"}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": f"unexpected:{type(exc).__name__}"}
    if not isinstance(payload, list):
        return {"ok": False, "error": "invalid_payload"}

    rows: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, list) or len(row) < 7:
            continue
        open_ms = int(to_float_nan(row[0]) if str(row[0]).strip() else 0)
        close_ms = int(to_float_nan(row[6]) if str(row[6]).strip() else 0)
        rows.append(
            {
                "open_time_ms": open_ms,
                "open": float(to_float_nan(row[1])),
                "high": float(to_float_nan(row[2])),
                "low": float(to_float_nan(row[3])),
                "close": float(to_float_nan(row[4])),
                "volume": float(to_float_nan(row[5])),
                "close_time_ms": close_ms,
                "open_time": _to_iso(open_ms),
                "close_time": _to_iso(close_ms),
            }
        )
    rows.sort(key=lambda item: int(item.get("open_time_ms", 0)))
    return {"ok": True, "rows": rows, "error": ""}


def _write_cache_rows(*, cache_dir: Path, symbol: str, timeframe: str, rows: list[dict[str, Any]]) -> str:
    root = cache_dir / symbol / timeframe
    root.mkdir(parents=True, exist_ok=True)
    if not rows:
        path = root / "empty.csv"
        if not path.exists():
            path.write_text("open_time_ms,open,high,low,close,volume,close_time_ms,open_time,close_time\n", encoding="utf-8")
        return str(path)
    first_ms = int(rows[0].get("open_time_ms", 0) or 0)
    first_day = datetime.fromtimestamp(first_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d") if first_ms > 0 else "unknown"
    path = root / f"{first_day}_backfill.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["open_time_ms", "open", "high", "low", "close", "volume", "close_time_ms", "open_time", "close_time"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "open_time_ms": row.get("open_time_ms", ""),
                    "open": row.get("open", ""),
                    "high": row.get("high", ""),
                    "low": row.get("low", ""),
                    "close": row.get("close", ""),
                    "volume": row.get("volume", ""),
                    "close_time_ms": row.get("close_time_ms", ""),
                    "open_time": row.get("open_time", ""),
                    "close_time": row.get("close_time", ""),
                }
            )
    return str(path)


def validate_backfill_execution_mode(*, execute_fetch: bool, dry_run: bool, write_cache: bool) -> dict[str, Any]:
    resolved_execute_fetch = bool(execute_fetch)
    resolved_dry_run = bool(dry_run) or (not resolved_execute_fetch)
    warnings: list[str] = []
    if (not resolved_execute_fetch) and bool(write_cache):
        warnings.append("write_cache_ignored_without_execute_fetch")
    if resolved_dry_run and bool(write_cache):
        warnings.append("write_cache_disabled_in_dry_run")
    return {
        "execute_fetch": resolved_execute_fetch,
        "dry_run": resolved_dry_run,
        "network_enabled": bool(resolved_execute_fetch and (not resolved_dry_run)),
        "warnings": warnings,
    }


def run_public_kline_backfill(
    *,
    plan_csv: str = "reports/kline_cache_backfill_plan/kline_cache_backfill_plan.csv",
    cache_dir: str = "data/cache/klines",
    output_dir: str = "reports/kline_cache_backfill",
    max_symbols: int = 5,
    max_bars: int = 1500,
    market: str = "futures",
    dry_run: bool = True,
    write_cache: bool = False,
    public_only: bool = False,
    min_written_bars: int = 100,
    fail_if_empty: bool = False,
    execute_fetch: bool = False,
) -> dict[str, Any]:
    resolved_cfg = normalize_kline_backfill_config(
        max_symbols=max_symbols,
        max_bars=max_bars,
        market=market,
        dry_run=dry_run,
        write_cache=write_cache,
        public_only=public_only,
        min_written_bars=min_written_bars,
        fail_if_empty=fail_if_empty,
    )
    plan_rows = read_csv_rows(Path(plan_csv))
    selected_rows = build_kline_request_windows(
        plan_rows=plan_rows,
        max_symbols=int(resolved_cfg.get("max_symbols", max_symbols)),
        max_bars=int(resolved_cfg.get("max_bars", max_bars)),
    )
    plan_summary = summarize_backfill_plan(plan_rows_total=len(plan_rows), windows=selected_rows)
    mode = validate_backfill_execution_mode(
        execute_fetch=bool(execute_fetch),
        dry_run=bool(resolved_cfg.get("dry_run", dry_run)),
        write_cache=bool(resolved_cfg.get("write_cache", write_cache)),
    )
    resolved_dry_run = bool(mode.get("dry_run", True))
    network_enabled = bool(mode.get("network_enabled", False))
    cache_root = Path(cache_dir)

    out_rows: list[dict[str, Any]] = []
    early_error = ""
    if network_enabled and bool(resolved_cfg.get("write_cache", write_cache)) and (not bool(resolved_cfg.get("public_only", public_only))):
        early_error = "write_cache_requires_public_only"
    for row in selected_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        requested_bars = max(1, int(row.get("requested_bars", 300) or 300))
        coverage_status = "DRY_RUN_ONLY" if resolved_dry_run else "FAILED"
        fetched_bars = 0
        written_bars = 0
        cache_file = ""
        first_open = ""
        last_open = ""
        error = ""

        if early_error:
            coverage_status = "FAILED"
            error = early_error
        elif network_enabled:
            fetched = _fetch_public_klines(
                symbol=symbol,
                timeframe=timeframe,
                limit=requested_bars,
                market=market,
            )
            if not bool(fetched.get("ok", False)):
                coverage_status = "FAILED"
                error = str(fetched.get("error", "fetch_failed"))
            else:
                rows = list(fetched.get("rows", []))
                fetched_bars = len(rows)
                if rows:
                    first_open = str(rows[0].get("open_time", ""))
                    last_open = str(rows[-1].get("open_time", ""))
                if bool(resolved_cfg.get("write_cache", write_cache)):
                    cache_file = _write_cache_rows(cache_dir=cache_root, symbol=symbol, timeframe=timeframe, rows=rows)
                    written_bars = len(rows)
                coverage_status = "OK" if fetched_bars >= min(50, requested_bars) else "PARTIAL"
                if written_bars <= 0 and bool(resolved_cfg.get("write_cache", write_cache)):
                    coverage_status = "FAILED"
                    error = "no_rows_written"
                if not bool(resolved_cfg.get("write_cache", write_cache)):
                    coverage_status = "DRY_RUN_ONLY"
        out_rows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "market": str(resolved_cfg.get("market", market or "futures")),
                "requested_bars": requested_bars,
                "fetched_bars": fetched_bars,
                "written_bars": written_bars,
                "cache_file": cache_file,
                "first_open_time": first_open,
                "last_open_time": last_open,
                "coverage_status": coverage_status,
                "dry_run": resolved_dry_run,
                "error": error,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "backfill_results.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    total_fetched_bars = sum(int(row.get("fetched_bars", 0) or 0) for row in out_rows)
    total_written_bars = sum(int(row.get("written_bars", 0) or 0) for row in out_rows)
    cache_write_verdict = "PASS"
    if bool(resolved_cfg.get("write_cache", write_cache)):
        if total_written_bars <= 0:
            cache_write_verdict = "FAIL"
        elif total_written_bars < int(resolved_cfg.get("min_written_bars", min_written_bars)):
            cache_write_verdict = "PARTIAL"

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS",
        "public_only": bool(resolved_cfg.get("public_only", public_only)),
        "write_cache": bool(resolved_cfg.get("write_cache", write_cache)),
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "min_written_bars": int(resolved_cfg.get("min_written_bars", min_written_bars)),
        "cache_write_verdict": cache_write_verdict,
        "plan_rows_total": int(plan_summary.get("plan_rows_total", len(plan_rows))),
        "selected_rows": int(plan_summary.get("selected_rows", len(selected_rows))),
        "market": str(resolved_cfg.get("market", market or "futures")),
        "execute_fetch": bool(mode.get("execute_fetch", False)),
        "network_enabled": network_enabled,
        "dry_run": resolved_dry_run,
        "fetched_bars_total": total_fetched_bars,
        "written_bars_total": total_written_bars,
        "total_fetched_bars": total_fetched_bars,
        "total_written_bars": total_written_bars,
        "ok_count": sum(1 for row in out_rows if str(row.get("coverage_status", "")).strip().upper() == "OK"),
        "partial_count": sum(1 for row in out_rows if str(row.get("coverage_status", "")).strip().upper() == "PARTIAL"),
        "failed_count": sum(1 for row in out_rows if str(row.get("coverage_status", "")).strip().upper() == "FAILED"),
        "dry_run_only_count": sum(1 for row in out_rows if str(row.get("coverage_status", "")).strip().upper() == "DRY_RUN_ONLY"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "symbols_requested": len(sorted({str(row.get("symbol", "")).strip().upper() for row in selected_rows if str(row.get("symbol", "")).strip()})),
        "symbols_written": len(
            sorted(
                {
                    str(row.get("symbol", "")).strip().upper()
                    for row in out_rows
                    if int(row.get("written_bars", 0) or 0) > 0 and str(row.get("symbol", "")).strip()
                }
            )
        ),
        "timeframes_written": sorted(
            {
                str(row.get("timeframe", "")).strip()
                for row in out_rows
                if int(row.get("written_bars", 0) or 0) > 0 and str(row.get("timeframe", "")).strip()
            }
        ),
        "failed_symbols": sorted(
            {
                str(row.get("symbol", "")).strip().upper()
                for row in out_rows
                if str(row.get("coverage_status", "")).strip().upper() == "FAILED" and str(row.get("symbol", "")).strip()
            }
        ),
        "cache_files_written": sorted(
            {str(row.get("cache_file", "")).strip() for row in out_rows if str(row.get("cache_file", "")).strip()}
        ),
        "warnings": list(mode.get("warnings", [])),
    }
    if early_error:
        summary["final_verdict"] = "FAIL"
        summary["error"] = early_error
    elif summary["failed_count"] > 0:
        summary["final_verdict"] = "PARTIAL"
    if cache_write_verdict == "FAIL":
        summary["final_verdict"] = "FAIL"
    elif (cache_write_verdict == "PARTIAL") and summary["final_verdict"] == "PASS":
        summary["final_verdict"] = "PARTIAL"
    if bool(write_cache) and bool(fail_if_empty) and total_written_bars <= 0:
        summary["final_verdict"] = "FAIL"
        summary["error"] = "empty_backfill_results"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Public Kline Backfill Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- selected_rows: {summary['selected_rows']}",
        f"- dry_run: {summary['dry_run']}",
        f"- write_cache: {summary['write_cache']}",
        f"- public_only: {summary['public_only']}",
        f"- fetched_bars_total: {summary['fetched_bars_total']}",
        f"- written_bars_total: {summary['written_bars_total']}",
        f"- cache_write_verdict: {summary['cache_write_verdict']}",
        f"- dry_run_only_count: {summary['dry_run_only_count']}",
        f"- failed_count: {summary['failed_count']}",
    ]
    if str(summary.get("error", "")).strip():
        lines.append(f"- error: {summary['error']}")
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run public-only kline cache backfill from plan")
    parser.add_argument("--plan-csv", default="reports/kline_cache_backfill_plan/kline_cache_backfill_plan.csv")
    parser.add_argument("--cache-dir", default="data/cache/klines")
    parser.add_argument("--output-dir", default="reports/kline_cache_backfill")
    parser.add_argument("--max-symbols", type=int, default=5)
    parser.add_argument("--max-bars", type=int, default=1500)
    parser.add_argument("--market", default="futures", choices=["futures", "spot"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-cache", action="store_true")
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument("--execute-fetch", action="store_true")
    parser.add_argument("--min-written-bars", type=int, default=100)
    parser.add_argument("--fail-if-empty", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_public_kline_backfill(
        plan_csv=str(args.plan_csv or "reports/kline_cache_backfill_plan/kline_cache_backfill_plan.csv"),
        cache_dir=str(args.cache_dir or "data/cache/klines"),
        output_dir=str(args.output_dir or "reports/kline_cache_backfill"),
        max_symbols=int(args.max_symbols or 5),
        max_bars=int(args.max_bars or 1500),
        market=str(args.market or "futures"),
        dry_run=bool(args.dry_run),
        write_cache=bool(args.write_cache),
        public_only=bool(args.public_only),
        execute_fetch=bool(args.execute_fetch),
        min_written_bars=int(args.min_written_bars if args.min_written_bars is not None else 100),
        fail_if_empty=bool(args.fail_if_empty),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"selected_rows={result.get('selected_rows', 0)}")
    print(f"written_bars_total={result.get('written_bars_total', 0)}")


if __name__ == "__main__":
    main()
