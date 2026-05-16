from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import (
    best_shadow_outcome_by_key,
    load_shadow_outcome_rows,
    load_shadow_plan_rows,
    match_plan_for_trade,
    nan_to_empty,
    read_csv_rows,
    safe_ratio,
    to_float,
    to_float_nan,
)


FIELDS = [
    "trade_id",
    "candidate_id",
    "symbol",
    "side",
    "timeframe",
    "signal_time",
    "entry_time",
    "entry_price",
    "outcome",
    "pnl_estimate_usdt",
    "realized_r_multiple",
    "mfe_r",
    "mae_r",
    "entry_timing_score",
    "trend_alignment_score",
    "breakout_quality_score",
    "risk_reward_score",
    "post_entry_followthrough_score",
    "signal_quality_score",
    "signal_grade",
    "signal_verdict",
    "reason",
    "source_reports",
]


def _grade(score: float, has_data: bool) -> str:
    if not has_data or (not math.isfinite(score)):
        return "UNKNOWN"
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _calc_scores(
    *,
    outcome: str,
    side: str,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    realized_r: float,
    mfe_r: float,
    mae_r: float,
    exit_efficiency_pct: float,
) -> tuple[dict[str, float], list[str]]:
    reasons: list[str] = []
    # Trend alignment
    trend_score = 10.0
    if outcome == "TAKE_PROFIT_TRIGGERED":
        trend_score = 18.0
    elif outcome == "STOP_LOSS_TRIGGERED":
        trend_score = 6.0
    elif math.isfinite(realized_r) and realized_r > 0:
        trend_score = 15.0
    elif math.isfinite(realized_r) and realized_r < 0:
        trend_score = 7.0

    # Breakout quality
    breakout_score = 10.0
    if math.isfinite(mfe_r):
        breakout_score = _clamp(8.0 + mfe_r * 6.0, 0.0, 20.0)
    elif math.isfinite(realized_r):
        breakout_score = _clamp(8.0 + realized_r * 5.0, 0.0, 20.0)
    else:
        reasons.append("missing_followthrough_data")

    # Entry timing
    entry_timing = 10.0
    if math.isfinite(exit_efficiency_pct):
        entry_timing = _clamp(10.0 + (exit_efficiency_pct - 100.0) * 0.08, 0.0, 20.0)
    elif math.isfinite(mae_r):
        entry_timing = _clamp(16.0 - mae_r * 8.0, 0.0, 20.0)
    else:
        reasons.append("missing_entry_timing_context")

    # Risk reward
    rr_score = 10.0
    risk_per_unit = abs(entry_price - sl_price) if entry_price > 0 and sl_price > 0 else float("nan")
    reward_per_unit = abs(tp_price - entry_price) if entry_price > 0 and tp_price > 0 else float("nan")
    rr = safe_ratio(reward_per_unit, risk_per_unit)
    if math.isfinite(rr):
        rr_score = _clamp(20.0 - abs(rr - 1.5) * 7.0, 0.0, 20.0)
    else:
        reasons.append("missing_rr_structure")

    # Post-entry followthrough
    follow_score = 10.0
    if math.isfinite(mfe_r) and math.isfinite(realized_r):
        capture = safe_ratio(max(realized_r, 0.0), max(mfe_r, 1e-9))
        if math.isfinite(capture):
            follow_score = _clamp(8.0 + capture * 10.0 + max(realized_r, 0.0) * 2.0, 0.0, 20.0)
    elif math.isfinite(realized_r):
        follow_score = _clamp(10.0 + realized_r * 6.0, 0.0, 20.0)
    else:
        reasons.append("missing_followthrough_r")

    scores = {
        "trend_alignment_score": round(trend_score, 6),
        "breakout_quality_score": round(breakout_score, 6),
        "entry_timing_score": round(entry_timing, 6),
        "risk_reward_score": round(rr_score, 6),
        "post_entry_followthrough_score": round(follow_score, 6),
    }
    return scores, reasons


def calculate_signal_quality_score(
    *,
    lifecycle_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    shadow_plan_jsonl: str = "logs/shadow_order_plans.jsonl",
    shadow_outcome_csv: str = "logs/shadow_order_outcomes.csv",
    shadow_candidate_outcomes_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv",
    output_dir: str = "reports/signal_quality",
) -> dict[str, Any]:
    lifecycle_rows = read_csv_rows(Path(lifecycle_csv))
    shadow_plans = load_shadow_plan_rows(shadow_plan_jsonl)
    shadow_outcomes = load_shadow_outcome_rows(shadow_outcome_csv)
    outcomes_by_key = best_shadow_outcome_by_key(shadow_outcomes)
    shadow_candidate_outcomes = read_csv_rows(Path(shadow_candidate_outcomes_csv))
    shadow_candidate_by_candidate = {
        str(row.get("shadow_candidate_id", "")).strip(): row
        for row in shadow_candidate_outcomes
        if str(row.get("shadow_candidate_id", "")).strip()
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scores_csv = out_dir / "signal_quality_scores.csv"
    summary_json = out_dir / "signal_quality_summary.json"
    summary_md = out_dir / "summary.md"

    rows: list[dict[str, Any]] = []
    for trade in lifecycle_rows:
        candidate_id = str(trade.get("candidate_id", "")).strip()
        plan = match_plan_for_trade(trade_row=trade, plans=shadow_plans)
        matched_outcome = outcomes_by_key.get(str(plan.get("order_key", "")).strip(), {}) if plan else {}
        if not matched_outcome and candidate_id:
            matched_outcome = shadow_candidate_by_candidate.get(candidate_id, {})
        symbol = str(trade.get("symbol", "")).strip().upper()
        side = str(trade.get("side", "")).strip().upper()
        outcome = str(trade.get("outcome", "")).strip().upper()
        entry_price = to_float_nan(trade.get("entry_price"))
        sl_price = to_float_nan(trade.get("sl_price"))
        tp_price = to_float_nan(trade.get("tp_price"))
        realized_r = to_float_nan(trade.get("realized_r_multiple"))
        mfe_r = to_float_nan(matched_outcome.get("mfe"))
        mae_r = to_float_nan(matched_outcome.get("mae"))
        exit_eff = to_float_nan(trade.get("exit_efficiency_pct"))
        scores, score_reasons = _calc_scores(
            outcome=outcome,
            side=side,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            realized_r=realized_r,
            mfe_r=mfe_r,
            mae_r=mae_r,
            exit_efficiency_pct=exit_eff,
        )
        has_score_data = bool(scores) and len(score_reasons) < 5
        total_score = float("nan")
        if has_score_data:
            total_score = sum(float(scores[key]) for key in scores.keys())
        grade = _grade(total_score, has_score_data)

        verdict = "FAIL"
        if (math.isfinite(total_score) and total_score >= 75.0 and ((math.isfinite(realized_r) and realized_r >= 0) or outcome == "TAKE_PROFIT_TRIGGERED")):
            verdict = "PASS"
        elif (math.isfinite(total_score) and total_score >= 60.0) or (grade == "UNKNOWN" and ((math.isfinite(realized_r) and realized_r > 0) or outcome == "TAKE_PROFIT_TRIGGERED")):
            verdict = "PARTIAL"
        elif math.isfinite(realized_r) and realized_r < -0.5:
            verdict = "FAIL"
        else:
            verdict = "PARTIAL" if outcome == "TAKE_PROFIT_TRIGGERED" else "FAIL"

        reasons = list(score_reasons)
        if grade == "UNKNOWN":
            reasons.append("insufficient_signal_features")
        if math.isfinite(realized_r) and realized_r > 0:
            reasons.append("positive_realized_r")
        if outcome == "TAKE_PROFIT_TRIGGERED":
            reasons.append("tp_outcome_supports_signal")

        row = {
            "trade_id": str(trade.get("trade_id", "")),
            "candidate_id": candidate_id,
            "symbol": symbol,
            "side": side,
            "timeframe": str(plan.get("timeframe", "5m") if plan else "5m"),
            "signal_time": str(plan.get("entry_timestamp", trade.get("entry_time", "")) if plan else trade.get("entry_time", "")),
            "entry_time": str(trade.get("entry_time", "")),
            "entry_price": nan_to_empty(entry_price),
            "outcome": outcome,
            "pnl_estimate_usdt": nan_to_empty(to_float_nan(trade.get("pnl_estimate_usdt"))),
            "realized_r_multiple": nan_to_empty(realized_r),
            "mfe_r": nan_to_empty(mfe_r),
            "mae_r": nan_to_empty(mae_r),
            "entry_timing_score": scores["entry_timing_score"],
            "trend_alignment_score": scores["trend_alignment_score"],
            "breakout_quality_score": scores["breakout_quality_score"],
            "risk_reward_score": scores["risk_reward_score"],
            "post_entry_followthrough_score": scores["post_entry_followthrough_score"],
            "signal_quality_score": nan_to_empty(total_score),
            "signal_grade": grade,
            "signal_verdict": verdict,
            "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            "source_reports": str(trade.get("source_reports", "")),
        }
        rows.append(row)

    with scores_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    numeric_scores = [to_float_nan(row.get("signal_quality_score")) for row in rows if math.isfinite(to_float_nan(row.get("signal_quality_score")))]
    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(rows),
        "pass_count": sum(1 for row in rows if str(row.get("signal_verdict", "")).strip().upper() == "PASS"),
        "partial_count": sum(1 for row in rows if str(row.get("signal_verdict", "")).strip().upper() == "PARTIAL"),
        "fail_count": sum(1 for row in rows if str(row.get("signal_verdict", "")).strip().upper() == "FAIL"),
        "unknown_grade_count": sum(1 for row in rows if str(row.get("signal_grade", "")).strip().upper() == "UNKNOWN"),
        "avg_signal_quality_score": round(sum(numeric_scores) / len(numeric_scores), 8) if numeric_scores else float("nan"),
        "shadow_candidate_outcomes_rows_loaded": len(shadow_candidate_outcomes),
        "scores_csv": str(scores_csv),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS"
    if summary["fail_count"] > 0:
        summary["final_verdict"] = "FAIL"
    elif summary["partial_count"] > 0 or summary["total_rows"] == 0:
        summary["final_verdict"] = "PARTIAL"

    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Signal Quality Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- pass_count: {summary['pass_count']}",
        f"- partial_count: {summary['partial_count']}",
        f"- fail_count: {summary['fail_count']}",
        f"- unknown_grade_count: {summary['unknown_grade_count']}",
        f"- avg_signal_quality_score: {summary['avg_signal_quality_score']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calculate signal quality score offline")
    parser.add_argument("--lifecycle-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--shadow-plan-jsonl", default="logs/shadow_order_plans.jsonl")
    parser.add_argument("--shadow-outcome-csv", default="logs/shadow_order_outcomes.csv")
    parser.add_argument("--shadow-candidate-outcomes-csv", default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv")
    parser.add_argument("--output-dir", default="reports/signal_quality")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = calculate_signal_quality_score(
        lifecycle_csv=str(args.lifecycle_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        shadow_plan_jsonl=str(args.shadow_plan_jsonl or "logs/shadow_order_plans.jsonl"),
        shadow_outcome_csv=str(args.shadow_outcome_csv or "logs/shadow_order_outcomes.csv"),
        shadow_candidate_outcomes_csv=str(args.shadow_candidate_outcomes_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv"),
        output_dir=str(args.output_dir or "reports/signal_quality"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"scores_csv={result.get('scores_csv', '')}")


if __name__ == "__main__":
    main()
