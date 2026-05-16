from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "symbol",
    "side",
    "timeframe",
    "sample_count",
    "win_rate",
    "avg_realized_r_multiple",
    "avg_signal_quality_score",
    "avg_execution_quality_score",
    "sample_confidence_level",
    "candidate_verdict",
    "recommendation",
    "risk_level",
    "reason",
    "next_action",
]


def _normalize_side(value: str) -> str:
    text = str(value or "").strip().upper()
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    if text in {"BUY", "LONG"}:
        return "LONG"
    return text or "UNKNOWN"


def generate_symbol_side_recommendations(
    *,
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    by_symbol_csv: str = "reports/trade_lifecycle_analysis/by_symbol.csv",
    execution_quality_summary_json: str = "reports/execution_quality/execution_quality_summary.json",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    output_dir: str = "reports/symbol_side_recommendations",
) -> dict[str, Any]:
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))
    by_symbol_rows = read_csv_rows(Path(by_symbol_csv))
    try:
        execution_quality = json.loads(Path(execution_quality_summary_json).read_text(encoding="utf-8")) if Path(execution_quality_summary_json).exists() else {}
    except (OSError, json.JSONDecodeError):
        execution_quality = {}
    try:
        system_health = json.loads(Path(system_health_json).read_text(encoding="utf-8")) if Path(system_health_json).exists() else {}
    except (OSError, json.JSONDecodeError):
        system_health = {}

    by_symbol_index = {str(row.get("group_key", "")).strip().upper(): row for row in by_symbol_rows if str(row.get("group_key", "")).strip()}
    anomaly = dict(system_health.get("anomaly_summary", {})) if isinstance(system_health.get("anomaly_summary", {}), dict) else {}
    has_critical_or_high = int(anomaly.get("critical_count", 0) or 0) > 0 or int(anomaly.get("high_count", 0) or 0) > 0

    rows: list[dict[str, Any]] = []
    for item in strategy_rows:
        symbol = str(item.get("symbol", "")).strip().upper()
        side = _normalize_side(str(item.get("side", "")))
        timeframe = str(item.get("timeframe", "5m") or "5m")
        sample_count = int(to_float_nan(item.get("sample_count")) if math.isfinite(to_float_nan(item.get("sample_count"))) else 0)
        win_rate = to_float_nan(item.get("win_rate"))
        avg_r = to_float_nan(item.get("avg_realized_r_multiple"))
        avg_signal = to_float_nan(item.get("avg_signal_quality_score"))
        avg_exec = to_float_nan(item.get("avg_execution_quality_score"))
        conf = str(item.get("sample_confidence_level", "UNKNOWN")).strip().upper()
        verdict = str(item.get("candidate_verdict", "UNKNOWN")).strip().upper()
        unknown_outcomes = int(to_float_nan(item.get("unknown_outcome_count")) if math.isfinite(to_float_nan(item.get("unknown_outcome_count"))) else 0)
        orphan_after = int(to_float_nan(item.get("orphan_after_close_count")) if math.isfinite(to_float_nan(item.get("orphan_after_close_count"))) else 0)
        reason_parts: list[str] = []

        # fallback exec quality from by_symbol/execution summary
        if not math.isfinite(avg_exec):
            by_symbol = by_symbol_index.get(symbol, {})
            avg_exec = to_float_nan(by_symbol.get("avg_execution_quality_score"))
        if not math.isfinite(avg_exec):
            avg_exec = to_float_nan(execution_quality.get("avg_execution_quality_score"))

        recommendation = "UNKNOWN"
        risk_level = "UNKNOWN"
        next_action = "manual_review"

        if sample_count < 5 and verdict != "FAIL":
            recommendation = "WATCH"
            risk_level = "LOW_SAMPLE"
            next_action = "collect_more_samples"
            reason_parts.append("sample_size_too_small")
        elif sample_count >= 20 and (
            (math.isfinite(avg_r) and avg_r < -0.3)
            or (math.isfinite(win_rate) and win_rate < 0.25)
            or orphan_after > 0
        ):
            recommendation = "BLACKLIST"
            risk_level = "HIGH_RISK"
            next_action = "disable_symbol_side"
            reason_parts.append("persistent_negative_performance")
        elif sample_count >= 10 and verdict == "FAIL":
            recommendation = "REJECT"
            risk_level = "HIGH_RISK"
            next_action = "reject_strategy_path"
            reason_parts.append("candidate_verdict_fail")
        elif sample_count >= 5 and (unknown_outcomes > 0 or (math.isfinite(avg_exec) and avg_exec < 80)):
            recommendation = "PAUSE"
            risk_level = "MEDIUM_RISK"
            next_action = "investigate_data_quality"
            reason_parts.append("unknown_or_low_execution_quality")
        elif sample_count >= 50 and (
            math.isfinite(avg_r)
            and avg_r > 0.2
            and math.isfinite(win_rate)
            and win_rate >= 0.45
            and math.isfinite(avg_exec)
            and avg_exec >= 90
            and math.isfinite(avg_signal)
            and avg_signal >= 75
            and (not has_critical_or_high)
        ):
            recommendation = "PROMOTE"
            risk_level = "LOW_RISK"
            next_action = "promote_to_observation"
            reason_parts.append("meets_promotion_threshold")
        elif sample_count >= 5 and (
            math.isfinite(avg_exec)
            and avg_exec >= 90
            and math.isfinite(avg_signal)
            and avg_signal >= 60
            and (not has_critical_or_high)
        ):
            recommendation = "ALLOW_TESTNET_SMALL_SIZE"
            risk_level = "CONTROLLED"
            next_action = "controlled_small_size_after_reset"
            reason_parts.append("meets_small_size_threshold")
        else:
            recommendation = "WATCH"
            risk_level = "LOW_SAMPLE" if sample_count < 20 else "MEDIUM_RISK"
            next_action = "collect_more_samples"
            reason_parts.append("insufficient_confidence")

        rows.append(
            {
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "sample_count": sample_count,
                "win_rate": win_rate,
                "avg_realized_r_multiple": avg_r,
                "avg_signal_quality_score": avg_signal,
                "avg_execution_quality_score": avg_exec,
                "sample_confidence_level": conf,
                "candidate_verdict": verdict,
                "recommendation": recommendation,
                "risk_level": risk_level,
                "reason": ";".join(sorted(set(reason_parts))) if reason_parts else "ok",
                "next_action": next_action,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "symbol_side_recommendations.csv"
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
        "total_rows": len(rows),
        "watch_count": sum(1 for row in rows if str(row.get("recommendation", "")).upper() == "WATCH"),
        "allow_small_size_count": sum(1 for row in rows if str(row.get("recommendation", "")).upper() == "ALLOW_TESTNET_SMALL_SIZE"),
        "promote_count": sum(1 for row in rows if str(row.get("recommendation", "")).upper() == "PROMOTE"),
        "pause_or_reject_count": sum(1 for row in rows if str(row.get("recommendation", "")).upper() in {"PAUSE", "REJECT", "BLACKLIST"}),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS"
    if summary["total_rows"] == 0:
        summary["final_verdict"] = "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Symbol Side Recommendations",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- watch_count: {summary['watch_count']}",
        f"- allow_small_size_count: {summary['allow_small_size_count']}",
        f"- promote_count: {summary['promote_count']}",
        f"- pause_or_reject_count: {summary['pause_or_reject_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate symbol/side recommendation report from strategy candidate score")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--by-symbol-csv", default="reports/trade_lifecycle_analysis/by_symbol.csv")
    parser.add_argument("--execution-quality-summary-json", default="reports/execution_quality/execution_quality_summary.json")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--output-dir", default="reports/symbol_side_recommendations")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_symbol_side_recommendations(
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        by_symbol_csv=str(args.by_symbol_csv or "reports/trade_lifecycle_analysis/by_symbol.csv"),
        execution_quality_summary_json=str(args.execution_quality_summary_json or "reports/execution_quality/execution_quality_summary.json"),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        output_dir=str(args.output_dir or "reports/symbol_side_recommendations"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
