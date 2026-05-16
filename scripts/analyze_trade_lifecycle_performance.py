from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GROUP_FIELDS = [
    "group_key",
    "trade_count",
    "tp_count",
    "sl_count",
    "manual_close_count",
    "unknown_count",
    "win_count",
    "loss_count",
    "win_rate",
    "total_pnl_estimate_usdt",
    "avg_pnl_estimate_usdt",
    "avg_pnl_pct_estimate",
    "avg_realized_r_multiple",
    "avg_execution_quality_score",
    "orphan_ever_detected_count",
    "orphan_after_close_count",
    "pass_count",
    "partial_count",
    "fail_count",
]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_float_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    text = str(value).strip()
    if not text:
        return float("nan")
    try:
        return float(text)
    except (TypeError, ValueError):
        return float("nan")


def _to_bool(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def _build_quality_maps(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_trade_id: dict[str, dict[str, Any]] = {}
    by_candidate_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        trade_id = str(row.get("trade_id", "")).strip()
        candidate_id = str(row.get("candidate_id", "")).strip()
        if trade_id:
            by_trade_id[trade_id] = row
        if candidate_id:
            by_candidate_id[candidate_id] = row
    return by_trade_id, by_candidate_id


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 8) if values else 0.0


def _group_rows(
    lifecycle_rows: list[dict[str, Any]],
    quality_by_trade: dict[str, dict[str, Any]],
    quality_by_candidate: dict[str, dict[str, Any]],
    group_field: str,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in lifecycle_rows:
        key = str(row.get(group_field, "")).strip().upper() or "UNKNOWN"
        buckets.setdefault(key, []).append(row)

    result: list[dict[str, Any]] = []
    for key in sorted(buckets.keys()):
        rows = buckets[key]
        tp_count = 0
        sl_count = 0
        manual_count = 0
        unknown_count = 0
        win_count = 0
        loss_count = 0
        orphan_ever_count = 0
        orphan_after_count = 0
        pass_count = 0
        partial_count = 0
        fail_count = 0
        total_pnl = 0.0
        pnl_values: list[float] = []
        pnl_pct_values: list[float] = []
        r_values: list[float] = []
        score_values: list[float] = []

        for row in rows:
            outcome = str(row.get("outcome", "")).strip().upper()
            if outcome == "TAKE_PROFIT_TRIGGERED":
                tp_count += 1
            elif outcome == "STOP_LOSS_TRIGGERED":
                sl_count += 1
            elif outcome == "MANUAL_FLATTENED":
                manual_count += 1
            elif outcome in {"UNKNOWN", "EXTERNAL_CLOSED", ""}:
                unknown_count += 1

            pnl = _to_float_nan(row.get("pnl_estimate_usdt"))
            if math.isfinite(pnl):
                total_pnl += pnl
                pnl_values.append(pnl)
                if pnl > 0:
                    win_count += 1
                elif pnl < 0:
                    loss_count += 1

            pnl_pct = _to_float_nan(row.get("pnl_pct_estimate"))
            if math.isfinite(pnl_pct):
                pnl_pct_values.append(pnl_pct)

            realized_r = _to_float_nan(row.get("realized_r_multiple"))
            if math.isfinite(realized_r):
                r_values.append(realized_r)

            if _to_bool(row.get("orphan_ever_detected", False)):
                orphan_ever_count += 1
            if _to_bool(row.get("orphan_after_close", False)):
                orphan_after_count += 1

            verdict = str(row.get("execution_verdict", "")).strip().upper()
            if verdict not in {"PASS", "PARTIAL", "FAIL"}:
                q = quality_by_trade.get(str(row.get("trade_id", "")).strip()) or quality_by_candidate.get(
                    str(row.get("candidate_id", "")).strip()
                )
                verdict = str((q or {}).get("final_verdict", "")).strip().upper()
            if verdict == "PASS":
                pass_count += 1
            elif verdict == "PARTIAL":
                partial_count += 1
            elif verdict == "FAIL":
                fail_count += 1

            q = quality_by_trade.get(str(row.get("trade_id", "")).strip()) or quality_by_candidate.get(
                str(row.get("candidate_id", "")).strip()
            )
            score = _to_float_nan((q or {}).get("execution_quality_score"))
            if math.isfinite(score):
                score_values.append(score)

        trade_count = len(rows)
        win_rate = (win_count / trade_count) if trade_count > 0 else 0.0
        result.append(
            {
                "group_key": key,
                "trade_count": trade_count,
                "tp_count": tp_count,
                "sl_count": sl_count,
                "manual_close_count": manual_count,
                "unknown_count": unknown_count,
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate": round(win_rate, 8),
                "total_pnl_estimate_usdt": round(total_pnl, 8),
                "avg_pnl_estimate_usdt": _avg(pnl_values),
                "avg_pnl_pct_estimate": _avg(pnl_pct_values),
                "avg_realized_r_multiple": _avg(r_values),
                "avg_execution_quality_score": _avg(score_values),
                "orphan_ever_detected_count": orphan_ever_count,
                "orphan_after_close_count": orphan_after_count,
                "pass_count": pass_count,
                "partial_count": partial_count,
                "fail_count": fail_count,
            }
        )
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=GROUP_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in GROUP_FIELDS})


def analyze_trade_lifecycle_performance(
    *,
    lifecycle_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    quality_csv: str = "reports/execution_quality/execution_quality_scores.csv",
    output_dir: str = "reports/trade_lifecycle_analysis",
) -> dict[str, Any]:
    lifecycle_path = Path(lifecycle_csv)
    quality_path = Path(quality_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lifecycle_rows = _read_csv_rows(lifecycle_path)
    quality_rows = _read_csv_rows(quality_path)
    quality_by_trade, quality_by_candidate = _build_quality_maps(quality_rows)

    by_symbol = _group_rows(lifecycle_rows, quality_by_trade, quality_by_candidate, "symbol")
    by_side = _group_rows(lifecycle_rows, quality_by_trade, quality_by_candidate, "side")
    by_outcome = _group_rows(lifecycle_rows, quality_by_trade, quality_by_candidate, "outcome")

    by_symbol_path = out_dir / "by_symbol.csv"
    by_side_path = out_dir / "by_side.csv"
    by_outcome_path = out_dir / "by_outcome.csv"
    summary_json_path = out_dir / "summary.json"
    summary_md_path = out_dir / "summary.md"

    _write_csv(by_symbol_path, by_symbol)
    _write_csv(by_side_path, by_side)
    _write_csv(by_outcome_path, by_outcome)

    all_scores = []
    all_r = []
    for row in lifecycle_rows:
        value = _to_float_nan(row.get("realized_r_multiple"))
        if math.isfinite(value):
            all_r.append(value)
        q = quality_by_trade.get(str(row.get("trade_id", "")).strip()) or quality_by_candidate.get(
            str(row.get("candidate_id", "")).strip()
        )
        score = _to_float_nan((q or {}).get("execution_quality_score"))
        if math.isfinite(score):
            all_scores.append(score)

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "lifecycle_csv": str(lifecycle_path),
        "quality_csv": str(quality_path),
        "trade_count": len(lifecycle_rows),
        "group_count_by_symbol": len(by_symbol),
        "group_count_by_side": len(by_side),
        "group_count_by_outcome": len(by_outcome),
        "avg_realized_r_multiple": _avg(all_r),
        "avg_execution_quality_score": _avg(all_scores),
        "by_symbol_csv": str(by_symbol_path),
        "by_side_csv": str(by_side_path),
        "by_outcome_csv": str(by_outcome_path),
        "summary_json": str(summary_json_path),
        "summary_md": str(summary_md_path),
    }
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Trade Lifecycle Analysis",
        "",
        f"- trade_count: {summary['trade_count']}",
        f"- group_count_by_symbol: {summary['group_count_by_symbol']}",
        f"- group_count_by_side: {summary['group_count_by_side']}",
        f"- group_count_by_outcome: {summary['group_count_by_outcome']}",
        f"- avg_realized_r_multiple: {summary['avg_realized_r_multiple']}",
        f"- avg_execution_quality_score: {summary['avg_execution_quality_score']}",
        "",
        f"- by_symbol_csv: {by_symbol_path}",
        f"- by_side_csv: {by_side_path}",
        f"- by_outcome_csv: {by_outcome_path}",
    ]
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze lifecycle performance by symbol/side/outcome")
    parser.add_argument("--lifecycle-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--quality-csv", default="reports/execution_quality/execution_quality_scores.csv")
    parser.add_argument("--output-dir", default="reports/trade_lifecycle_analysis")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = analyze_trade_lifecycle_performance(
        lifecycle_csv=str(args.lifecycle_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        quality_csv=str(args.quality_csv or "reports/execution_quality/execution_quality_scores.csv"),
        output_dir=str(args.output_dir or "reports/trade_lifecycle_analysis"),
    )
    if bool(args.json):
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(f"trade_count={summary.get('trade_count', 0)}")
    print(f"avg_execution_quality_score={summary.get('avg_execution_quality_score', 0.0)}")
    print(f"summary_json={summary.get('summary_json', '')}")


if __name__ == "__main__":
    main()
