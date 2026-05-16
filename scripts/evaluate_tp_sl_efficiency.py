from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_bool, to_float_nan


FIELDS = [
    "trade_id",
    "candidate_id",
    "symbol",
    "side",
    "outcome",
    "risk_reward_ratio",
    "planned_tp_r_multiple",
    "realized_r_multiple",
    "mfe_r",
    "mae_r",
    "mfe_capture_ratio",
    "exit_efficiency_pct",
    "tp_efficiency_status",
    "sl_efficiency_status",
    "suggested_tp_adjustment",
    "suggested_sl_adjustment",
    "suggested_trailing_action",
    "efficiency_score",
    "verdict",
    "reason",
]


def _index_by_trade(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("trade_id", "")).strip()
        if key:
            mapping[key] = row
    return mapping


def _index_by_candidate(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("candidate_id", "")).strip()
        if key:
            mapping[key] = row
    return mapping


def evaluate_tp_sl_efficiency(
    *,
    lifecycle_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    mfe_mae_csv: str = "reports/post_entry_mfe_mae/post_entry_mfe_mae.csv",
    output_dir: str = "reports/tp_sl_efficiency",
) -> dict[str, Any]:
    lifecycle_rows = read_csv_rows(Path(lifecycle_csv))
    mfe_rows = read_csv_rows(Path(mfe_mae_csv))
    by_trade = _index_by_trade(mfe_rows)
    by_candidate = _index_by_candidate(mfe_rows)

    rows: list[dict[str, Any]] = []
    for trade in lifecycle_rows:
        trade_id = str(trade.get("trade_id", "")).strip()
        candidate_id = str(trade.get("candidate_id", "")).strip()
        mfe_row = by_trade.get(trade_id) or by_candidate.get(candidate_id) or {}
        outcome = str(trade.get("outcome", "")).strip().upper()

        planned_rr = to_float_nan(trade.get("risk_reward_ratio"))
        planned_tp_r = to_float_nan(trade.get("planned_tp_r_multiple"))
        realized_r = to_float_nan(trade.get("realized_r_multiple"))
        mfe_r = to_float_nan(mfe_row.get("mfe_r"))
        mae_r = to_float_nan(mfe_row.get("mae_r"))
        mfe_capture = to_float_nan(mfe_row.get("mfe_capture_ratio"))
        exit_eff = to_float_nan(trade.get("exit_efficiency_pct"))
        tp_reachable = to_bool(mfe_row.get("tp_was_reachable", False))
        sl_reachable = to_bool(mfe_row.get("sl_was_reachable", False))
        stop_distance_pct = to_float_nan(trade.get("stop_distance_pct"))
        analysis_status = str(mfe_row.get("analysis_status", "")).strip().upper()

        reasons: list[str] = []
        tp_status = "UNKNOWN"
        if outcome == "TAKE_PROFIT_TRIGGERED":
            tp_status = "REACHED"
        elif tp_reachable:
            tp_status = "REACHABLE_NOT_CAPTURED"
            reasons.append("tp_reachable_but_not_triggered")
        elif outcome == "STOP_LOSS_TRIGGERED":
            tp_status = "NOT_REACHED"
        else:
            tp_status = "UNKNOWN"

        sl_status = "UNKNOWN"
        if outcome == "STOP_LOSS_TRIGGERED":
            sl_status = "REACHED"
        elif sl_reachable and outcome != "STOP_LOSS_TRIGGERED":
            sl_status = "TOUCHED_SURVIVED"
            reasons.append("sl_touched_but_survived")
        elif outcome == "TAKE_PROFIT_TRIGGERED":
            sl_status = "NOT_REACHED"
        else:
            sl_status = "UNKNOWN"

        suggested_tp = "KEEP_TP"
        suggested_sl = "KEEP_SL"
        suggested_trailing = "NO_CHANGE"

        if math.isfinite(mfe_r) and math.isfinite(planned_tp_r) and planned_tp_r > 0:
            if mfe_r >= planned_tp_r * 1.5 and (not math.isfinite(mfe_capture) or mfe_capture < 0.8):
                suggested_tp = "INCREASE_TP_DISTANCE"
                suggested_trailing = "ENABLE_TRAILING_TAKE_PROFIT"
                reasons.append("tp_may_be_too_near")
            elif outcome != "TAKE_PROFIT_TRIGGERED" and mfe_r < planned_tp_r * 0.7:
                suggested_tp = "DECREASE_TP_DISTANCE"
                reasons.append("tp_may_be_too_far")

        if sl_reachable and math.isfinite(mfe_r) and mfe_r >= 1.0 and outcome != "STOP_LOSS_TRIGGERED":
            suggested_sl = "WIDEN_SL_OR_DELAY_ENTRY"
            reasons.append("sl_may_be_too_near")
        elif math.isfinite(mae_r) and mae_r < 0.3 and math.isfinite(stop_distance_pct) and stop_distance_pct > 3.0:
            suggested_sl = "TIGHTEN_SL"
            reasons.append("sl_may_be_too_wide")

        score = 60.0
        if outcome == "TAKE_PROFIT_TRIGGERED":
            score += 20.0
        elif outcome == "STOP_LOSS_TRIGGERED":
            score -= 15.0
        if math.isfinite(realized_r):
            score += max(-20.0, min(20.0, realized_r * 10.0))
        if math.isfinite(mfe_capture):
            score += max(-10.0, min(10.0, (mfe_capture - 0.6) * 25.0))
        if analysis_status in {"MISSING_KLINES", "PARTIAL"}:
            score -= 5.0
            reasons.append("insufficient_post_entry_klines")
        score = max(0.0, min(100.0, score))

        verdict = "PASS"
        if analysis_status in {"MISSING_KLINES", "PARTIAL"}:
            verdict = "PARTIAL"
        elif score < 60:
            verdict = "FAIL"
        elif score < 75:
            verdict = "PARTIAL"
        if outcome == "TAKE_PROFIT_TRIGGERED" and verdict == "FAIL":
            verdict = "PARTIAL"
        if tp_status == "REACHED" and verdict == "FAIL":
            verdict = "PARTIAL"

        rows.append(
            {
                "trade_id": trade_id,
                "candidate_id": candidate_id,
                "symbol": str(trade.get("symbol", "")).strip().upper(),
                "side": str(trade.get("side", "")).strip().upper(),
                "outcome": outcome,
                "risk_reward_ratio": planned_rr,
                "planned_tp_r_multiple": planned_tp_r,
                "realized_r_multiple": realized_r,
                "mfe_r": mfe_r,
                "mae_r": mae_r,
                "mfe_capture_ratio": mfe_capture,
                "exit_efficiency_pct": exit_eff,
                "tp_efficiency_status": tp_status,
                "sl_efficiency_status": sl_status,
                "suggested_tp_adjustment": suggested_tp,
                "suggested_sl_adjustment": suggested_sl,
                "suggested_trailing_action": suggested_trailing,
                "efficiency_score": round(score, 8),
                "verdict": verdict,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "tp_sl_efficiency.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    scores = [to_float_nan(row.get("efficiency_score")) for row in rows if math.isfinite(to_float_nan(row.get("efficiency_score")))]
    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(rows),
        "pass_count": sum(1 for row in rows if str(row.get("verdict", "")).strip().upper() == "PASS"),
        "partial_count": sum(1 for row in rows if str(row.get("verdict", "")).strip().upper() == "PARTIAL"),
        "fail_count": sum(1 for row in rows if str(row.get("verdict", "")).strip().upper() == "FAIL"),
        "avg_efficiency_score": round(sum(scores) / len(scores), 8) if scores else float("nan"),
        "csv_path": str(csv_path),
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
        "# TP/SL Efficiency Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- pass_count: {summary['pass_count']}",
        f"- partial_count: {summary['partial_count']}",
        f"- fail_count: {summary['fail_count']}",
        f"- avg_efficiency_score: {summary['avg_efficiency_score']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate TP/SL efficiency from lifecycle + MFE/MAE reports")
    parser.add_argument("--lifecycle-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--mfe-mae-csv", default="reports/post_entry_mfe_mae/post_entry_mfe_mae.csv")
    parser.add_argument("--output-dir", default="reports/tp_sl_efficiency")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_tp_sl_efficiency(
        lifecycle_csv=str(args.lifecycle_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        mfe_mae_csv=str(args.mfe_mae_csv or "reports/post_entry_mfe_mae/post_entry_mfe_mae.csv"),
        output_dir=str(args.output_dir or "reports/tp_sl_efficiency"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
