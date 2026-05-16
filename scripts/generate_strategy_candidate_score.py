from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import (
    compute_weighted_sample_count_with_observation,
    evaluate_weighted_sample_confidence,
    read_csv_rows,
    sample_mix_status,
    to_float_nan,
)


FIELDS = [
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "param_signature",
    "sample_count",
    "real_sample_count",
    "shadow_sample_count",
    "shadow_weight",
    "strict_shadow_sample_count",
    "observation_shadow_sample_count",
    "observation_shadow_weight",
    "weighted_observation_sample_count",
    "weighted_sample_count",
    "shadow_tp_count",
    "shadow_sl_count",
    "shadow_win_rate",
    "avg_shadow_realized_r_multiple",
    "sample_mix_status",
    "tp_count",
    "sl_count",
    "win_rate",
    "avg_pnl_pct_estimate",
    "avg_realized_r_multiple",
    "avg_mfe_r",
    "avg_mae_r",
    "avg_signal_quality_score",
    "avg_execution_quality_score",
    "avg_efficiency_score",
    "orphan_after_close_count",
    "unknown_outcome_count",
    "minimum_required_samples",
    "sample_confidence_score",
    "sample_confidence_level",
    "is_sample_size_sufficient",
    "confidence_reason",
    "strategy_candidate_score",
    "candidate_grade",
    "candidate_verdict",
    "reason",
]


def _grade(score: float) -> str:
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


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def _to_key(symbol: str, side: str, timeframe: str, param_signature: str) -> str:
    base = f"{symbol}_{'SHORT' if side in {'SELL', 'SHORT'} else 'LONG'}_{timeframe}"
    if param_signature and param_signature != "N/A":
        return f"{base}_{param_signature}"
    return base


def generate_strategy_candidate_score(
    *,
    shadow_outcome_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv",
    shadow_candidates_csv: str = "reports/shadow_candidate_collection/shadow_candidates.csv",
    shadow_universe_candidates_csv: str = "reports/shadow_universe_collection/shadow_universe_candidates.csv",
    lifecycle_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    signal_quality_csv: str = "reports/signal_quality/signal_quality_scores.csv",
    tp_sl_efficiency_csv: str = "reports/tp_sl_efficiency/tp_sl_efficiency.csv",
    by_symbol_csv: str = "reports/trade_lifecycle_analysis/by_symbol.csv",
    output_dir: str = "reports/strategy_candidate_score",
    shadow_sample_weight: float = 0.3,
    observation_shadow_weight: float = 0.1,
) -> dict[str, Any]:
    shadow_rows = read_csv_rows(Path(shadow_outcome_csv))
    shadow_candidates_rows = read_csv_rows(Path(shadow_candidates_csv))
    shadow_universe_rows = read_csv_rows(Path(shadow_universe_candidates_csv))
    lifecycle_rows = read_csv_rows(Path(lifecycle_csv))
    signal_rows = read_csv_rows(Path(signal_quality_csv))
    eff_rows = read_csv_rows(Path(tp_sl_efficiency_csv))
    by_symbol_rows = read_csv_rows(Path(by_symbol_csv))

    signal_by_trade = {str(row.get("trade_id", "")).strip(): row for row in signal_rows if str(row.get("trade_id", "")).strip()}
    signal_by_candidate = {str(row.get("candidate_id", "")).strip(): row for row in signal_rows if str(row.get("candidate_id", "")).strip()}
    eff_by_trade = {str(row.get("trade_id", "")).strip(): row for row in eff_rows if str(row.get("trade_id", "")).strip()}
    eff_by_candidate = {str(row.get("candidate_id", "")).strip(): row for row in eff_rows if str(row.get("candidate_id", "")).strip()}
    by_symbol_index = {
        str(row.get("group_key", "")).strip().upper(): row
        for row in by_symbol_rows
        if str(row.get("group_key", "")).strip()
    }

    groups: dict[str, list[dict[str, Any]]] = {}
    shadow_groups: dict[str, list[dict[str, Any]]] = {}
    meta: dict[str, dict[str, str]] = {}
    shadow_candidate_index: dict[str, dict[str, Any]] = {}
    for row in shadow_candidates_rows + shadow_universe_rows:
        cid = str(row.get("candidate_id", row.get("shadow_candidate_id", ""))).strip()
        if cid:
            shadow_candidate_index[cid] = {**shadow_candidate_index.get(cid, {}), **row}

    for trade in lifecycle_rows:
        trade_id = str(trade.get("trade_id", "")).strip()
        candidate_id = str(trade.get("candidate_id", "")).strip()
        signal_row = signal_by_trade.get(trade_id) or signal_by_candidate.get(candidate_id) or {}
        eff_row = eff_by_trade.get(trade_id) or eff_by_candidate.get(candidate_id) or {}

        symbol = str(trade.get("symbol", "")).strip().upper()
        side = str(trade.get("side", "")).strip().upper() or "BUY"
        timeframe = str(signal_row.get("timeframe", "5m") or "5m")
        param_signature = "N/A"
        key = _to_key(symbol, side, timeframe, param_signature)
        meta[key] = {
            "symbol": symbol,
            "side": side,
            "timeframe": timeframe,
            "param_signature": param_signature,
        }
        groups.setdefault(key, []).append(
            {
                "trade": trade,
                "signal": signal_row,
                "eff": eff_row,
            }
        )
    for shadow in shadow_rows:
        strategy_key = str(shadow.get("strategy_key", "")).strip()
        symbol = str(shadow.get("symbol", "")).strip().upper()
        if (not strategy_key) and (not symbol):
            continue
        side_raw = str(shadow.get("side", "")).strip().upper()
        side = "SHORT" if side_raw in {"SELL", "SHORT"} else "LONG" if side_raw in {"BUY", "LONG"} else (side_raw or "LONG")
        timeframe = str(shadow.get("timeframe", "5m")).strip() or "5m"
        if not strategy_key:
            strategy_key = _to_key(symbol, side, timeframe, "N/A")
        if strategy_key not in meta:
            meta[strategy_key] = {
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "param_signature": "N/A",
            }
        shadow_groups.setdefault(strategy_key, []).append(dict(shadow))

    out_rows: list[dict[str, Any]] = []
    strategy_keys = sorted(set(groups.keys()) | set(shadow_groups.keys()) | set(meta.keys()))
    for key in strategy_keys:
        items = groups.get(key, [])
        m = meta.get(
            key,
            {
                "symbol": "",
                "side": "LONG",
                "timeframe": "5m",
                "param_signature": "N/A",
            },
        )
        real_sample_count = len(items)
        tp_count = 0
        sl_count = 0
        wins = 0
        pnl_pct_values: list[float] = []
        realized_r_values: list[float] = []
        mfe_r_values: list[float] = []
        mae_r_values: list[float] = []
        signal_score_values: list[float] = []
        efficiency_values: list[float] = []
        orphan_after_close_count = 0
        unknown_outcome_count = 0
        execution_scores: list[float] = []
        by_symbol = by_symbol_index.get(m["symbol"], {})
        symbol_exec = to_float_nan(by_symbol.get("avg_execution_quality_score"))
        if math.isfinite(symbol_exec):
            execution_scores.append(symbol_exec)

        for item in items:
            trade = dict(item["trade"])
            signal = dict(item["signal"])
            eff = dict(item["eff"])
            outcome = str(trade.get("outcome", "")).strip().upper()
            if outcome == "TAKE_PROFIT_TRIGGERED":
                tp_count += 1
            if outcome == "STOP_LOSS_TRIGGERED":
                sl_count += 1
            if outcome in {"UNKNOWN", "EXTERNAL_CLOSED", ""}:
                unknown_outcome_count += 1
            if str(trade.get("orphan_after_close", "")).strip().lower() in {"1", "true", "yes", "y"}:
                orphan_after_close_count += 1

            pnl_pct = to_float_nan(trade.get("pnl_pct_estimate"))
            realized_r = to_float_nan(trade.get("realized_r_multiple"))
            mfe_r = to_float_nan(eff.get("mfe_r"))
            mae_r = to_float_nan(eff.get("mae_r"))
            signal_score = to_float_nan(signal.get("signal_quality_score"))
            efficiency_score = to_float_nan(eff.get("efficiency_score"))

            if math.isfinite(pnl_pct):
                pnl_pct_values.append(pnl_pct)
            if math.isfinite(realized_r):
                realized_r_values.append(realized_r)
                if realized_r > 0:
                    wins += 1
            else:
                pnl_usdt = to_float_nan(trade.get("pnl_estimate_usdt"))
                if math.isfinite(pnl_usdt) and pnl_usdt > 0:
                    wins += 1
            if math.isfinite(mfe_r):
                mfe_r_values.append(mfe_r)
            if math.isfinite(mae_r):
                mae_r_values.append(mae_r)
            if math.isfinite(signal_score):
                signal_score_values.append(signal_score)
            if math.isfinite(efficiency_score):
                efficiency_values.append(efficiency_score)

        shadow_items = shadow_groups.get(key, [])
        shadow_sample_count = len(shadow_items)
        strict_shadow_sample_count = 0
        observation_shadow_sample_count = 0
        shadow_tp_count = 0
        shadow_sl_count = 0
        shadow_wins = 0
        shadow_r_values: list[float] = []
        for shadow in shadow_items:
            cid = str(shadow.get("shadow_candidate_id", shadow.get("candidate_id", ""))).strip()
            cmeta = shadow_candidate_index.get(cid, {})
            cstatus = str(cmeta.get("candidate_status", "")).strip().upper()
            c_near_miss = str(cmeta.get("near_miss", "")).strip().lower() in {"1", "true", "yes", "y"}
            is_observation = bool(cstatus == "SHADOW_OBSERVATION_ONLY" or c_near_miss)
            if is_observation:
                observation_shadow_sample_count += 1
            else:
                strict_shadow_sample_count += 1
            outcome = str(shadow.get("outcome", "")).strip().upper()
            if outcome == "SHADOW_TP_FIRST":
                shadow_tp_count += 1
            if outcome == "SHADOW_SL_FIRST":
                shadow_sl_count += 1
            realized_r_shadow = to_float_nan(shadow.get("realized_r_multiple"))
            if math.isfinite(realized_r_shadow):
                shadow_r_values.append(realized_r_shadow)
                if realized_r_shadow > 0:
                    shadow_wins += 1
            elif outcome in {"SHADOW_TP_FIRST", "SHADOW_TIMEOUT_PROFIT"}:
                shadow_wins += 1

        weighted_sample_count = compute_weighted_sample_count_with_observation(
            real_sample_count=real_sample_count,
            strict_shadow_sample_count=strict_shadow_sample_count,
            observation_shadow_sample_count=observation_shadow_sample_count,
            strict_shadow_sample_weight=shadow_sample_weight,
            observation_shadow_sample_weight=observation_shadow_weight,
        )
        weighted_observation_sample_count = observation_shadow_sample_count * float(observation_shadow_weight)
        mix_status = sample_mix_status(real_sample_count=real_sample_count, shadow_sample_count=shadow_sample_count)

        sample_count = real_sample_count
        win_rate = wins / real_sample_count if real_sample_count > 0 else 0.0
        avg_realized_r = _avg(realized_r_values)
        avg_mfe_r = _avg(mfe_r_values)
        avg_mae_r = _avg(mae_r_values)
        avg_signal_score = _avg(signal_score_values)
        avg_exec_score = _avg(execution_scores)
        avg_efficiency = _avg(efficiency_values)
        avg_pnl_pct = _avg(pnl_pct_values)
        shadow_win_rate = (shadow_wins / shadow_sample_count) if shadow_sample_count > 0 else float("nan")
        avg_shadow_realized_r = _avg(shadow_r_values)

        quality_component = (win_rate * 15.0) + (max(0.0, min(2.0, (avg_realized_r if math.isfinite(avg_realized_r) else 0.0))) / 2.0 * 10.0)
        r_component = max(0.0, min(25.0, (avg_realized_r if math.isfinite(avg_realized_r) else 0.0) * 12.5))
        structure_component = 0.0
        if math.isfinite(avg_mfe_r) and math.isfinite(avg_mae_r):
            structure_component = max(0.0, min(20.0, (avg_mfe_r / max(0.1, avg_mae_r)) * 6.0))
        signal_component = max(0.0, min(15.0, (avg_signal_score if math.isfinite(avg_signal_score) else 0.0) / 100.0 * 15.0))
        exec_component = max(0.0, min(10.0, (avg_exec_score if math.isfinite(avg_exec_score) else 0.0) / 100.0 * 10.0))
        sample_component = max(0.0, min(5.0, weighted_sample_count / 20.0 * 5.0))
        candidate_score = quality_component + r_component + structure_component + signal_component + exec_component + sample_component
        candidate_score = max(0.0, min(100.0, candidate_score))

        confidence = evaluate_weighted_sample_confidence(
            weighted_sample_count=weighted_sample_count,
            minimum_required_samples=20,
        )
        confidence_level = str(confidence.get("sample_confidence_level", "TOO_SMALL"))
        reasons: list[str] = [str(confidence.get("confidence_reason", "")).strip()]
        verdict = "PASS"
        if confidence_level in {"TOO_SMALL", "LOW"}:
            verdict = "PARTIAL"
            if confidence_level == "TOO_SMALL":
                reasons.append("sample_size_too_small")
            else:
                reasons.append("sample_size_low")
        if unknown_outcome_count > 0:
            verdict = "PARTIAL"
            reasons.append("contains_unknown_outcomes")
        if orphan_after_close_count > 0:
            verdict = "PARTIAL"
            reasons.append("contains_orphan_after_close")
        if candidate_score < 60:
            verdict = "FAIL"
            reasons.append("low_candidate_score")
        elif candidate_score < 75 and verdict == "PASS":
            verdict = "PARTIAL"
            reasons.append("candidate_score_not_strong_enough")
        if weighted_sample_count < 20 and verdict == "PASS":
            verdict = "PARTIAL"
            reasons.append("insufficient_confidence_sample_size")
        if real_sample_count < 3 and verdict == "PASS":
            verdict = "PARTIAL"
            reasons.append("real_sample_count_below_three")
        if real_sample_count <= 0 and verdict == "PASS":
            verdict = "PARTIAL"
            reasons.append("no_real_trade_samples")
        if weighted_sample_count >= 20 and real_sample_count <= 0 and verdict == "PASS":
            verdict = "PARTIAL"
            reasons.append("weighted_without_real_samples")
        if confidence_level in {"TOO_SMALL", "LOW"} and verdict == "FAIL":
            verdict = "PARTIAL"
            reasons.append("confidence_cap_partial")

        is_sample_size_sufficient = bool(confidence.get("is_sample_size_sufficient", False)) and real_sample_count >= 3

        out_rows.append(
            {
                "strategy_key": key,
                "symbol": m["symbol"],
                "side": m["side"],
                "timeframe": m["timeframe"],
                "param_signature": m["param_signature"],
                "sample_count": sample_count,
                "real_sample_count": real_sample_count,
                "shadow_sample_count": shadow_sample_count,
                "shadow_weight": round(float(shadow_sample_weight), 8),
                "strict_shadow_sample_count": strict_shadow_sample_count,
                "observation_shadow_sample_count": observation_shadow_sample_count,
                "observation_shadow_weight": round(float(observation_shadow_weight), 8),
                "weighted_observation_sample_count": round(weighted_observation_sample_count, 8),
                "weighted_sample_count": round(weighted_sample_count, 8),
                "shadow_tp_count": shadow_tp_count,
                "shadow_sl_count": shadow_sl_count,
                "shadow_win_rate": round(shadow_win_rate, 8) if math.isfinite(shadow_win_rate) else float("nan"),
                "avg_shadow_realized_r_multiple": round(avg_shadow_realized_r, 8) if math.isfinite(avg_shadow_realized_r) else float("nan"),
                "sample_mix_status": mix_status,
                "tp_count": tp_count,
                "sl_count": sl_count,
                "win_rate": round(win_rate, 8),
                "avg_pnl_pct_estimate": round(avg_pnl_pct, 8) if math.isfinite(avg_pnl_pct) else float("nan"),
                "avg_realized_r_multiple": round(avg_realized_r, 8) if math.isfinite(avg_realized_r) else float("nan"),
                "avg_mfe_r": round(avg_mfe_r, 8) if math.isfinite(avg_mfe_r) else float("nan"),
                "avg_mae_r": round(avg_mae_r, 8) if math.isfinite(avg_mae_r) else float("nan"),
                "avg_signal_quality_score": round(avg_signal_score, 8) if math.isfinite(avg_signal_score) else float("nan"),
                "avg_execution_quality_score": round(avg_exec_score, 8) if math.isfinite(avg_exec_score) else float("nan"),
                "avg_efficiency_score": round(avg_efficiency, 8) if math.isfinite(avg_efficiency) else float("nan"),
                "orphan_after_close_count": orphan_after_close_count,
                "unknown_outcome_count": unknown_outcome_count,
                "minimum_required_samples": int(confidence.get("minimum_required_samples", 20)),
                "sample_confidence_score": float(confidence.get("sample_confidence_score", 0.0)),
                "sample_confidence_level": confidence_level,
                "is_sample_size_sufficient": bool(is_sample_size_sufficient),
                "confidence_reason": str(confidence.get("confidence_reason", "")),
                "strategy_candidate_score": round(candidate_score, 8),
                "candidate_grade": _grade(candidate_score),
                "candidate_verdict": verdict,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "strategy_candidate_score.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    scores = [to_float_nan(row.get("strategy_candidate_score")) for row in out_rows if math.isfinite(to_float_nan(row.get("strategy_candidate_score")))]
    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_count": len(out_rows),
        "pass_count": sum(1 for row in out_rows if str(row.get("candidate_verdict", "")).strip().upper() == "PASS"),
        "partial_count": sum(1 for row in out_rows if str(row.get("candidate_verdict", "")).strip().upper() == "PARTIAL"),
        "fail_count": sum(1 for row in out_rows if str(row.get("candidate_verdict", "")).strip().upper() == "FAIL"),
        "too_small_count": sum(1 for row in out_rows if str(row.get("sample_confidence_level", "")).strip().upper() == "TOO_SMALL"),
        "low_confidence_count": sum(1 for row in out_rows if str(row.get("sample_confidence_level", "")).strip().upper() == "LOW"),
        "avg_strategy_candidate_score": round(sum(scores) / len(scores), 8) if scores else float("nan"),
        "avg_weighted_sample_count": round(
            sum(to_float_nan(row.get("weighted_sample_count")) for row in out_rows if math.isfinite(to_float_nan(row.get("weighted_sample_count"))))
            / max(1, len([row for row in out_rows if math.isfinite(to_float_nan(row.get("weighted_sample_count")))])),
            8,
        )
        if out_rows
        else float("nan"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS"
    if summary["fail_count"] > 0:
        summary["final_verdict"] = "FAIL"
    elif summary["partial_count"] > 0 or summary["strategy_count"] == 0:
        summary["final_verdict"] = "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Strategy Candidate Score Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- strategy_count: {summary['strategy_count']}",
        f"- pass_count: {summary['pass_count']}",
        f"- partial_count: {summary['partial_count']}",
        f"- fail_count: {summary['fail_count']}",
        f"- too_small_count: {summary['too_small_count']}",
        f"- low_confidence_count: {summary['low_confidence_count']}",
        f"- avg_strategy_candidate_score: {summary['avg_strategy_candidate_score']}",
        f"- avg_weighted_sample_count: {summary['avg_weighted_sample_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate strategy candidate score from offline reports")
    parser.add_argument("--shadow-outcome-csv", default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv")
    parser.add_argument("--shadow-candidates-csv", default="reports/shadow_candidate_collection/shadow_candidates.csv")
    parser.add_argument("--shadow-universe-candidates-csv", default="reports/shadow_universe_collection/shadow_universe_candidates.csv")
    parser.add_argument("--lifecycle-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--signal-quality-csv", default="reports/signal_quality/signal_quality_scores.csv")
    parser.add_argument("--tp-sl-efficiency-csv", default="reports/tp_sl_efficiency/tp_sl_efficiency.csv")
    parser.add_argument("--by-symbol-csv", default="reports/trade_lifecycle_analysis/by_symbol.csv")
    parser.add_argument("--shadow-sample-weight", type=float, default=0.3)
    parser.add_argument("--observation-shadow-weight", type=float, default=0.1)
    parser.add_argument("--output-dir", default="reports/strategy_candidate_score")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_strategy_candidate_score(
        shadow_outcome_csv=str(args.shadow_outcome_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv"),
        shadow_candidates_csv=str(args.shadow_candidates_csv or "reports/shadow_candidate_collection/shadow_candidates.csv"),
        shadow_universe_candidates_csv=str(args.shadow_universe_candidates_csv or "reports/shadow_universe_collection/shadow_universe_candidates.csv"),
        lifecycle_csv=str(args.lifecycle_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        signal_quality_csv=str(args.signal_quality_csv or "reports/signal_quality/signal_quality_scores.csv"),
        tp_sl_efficiency_csv=str(args.tp_sl_efficiency_csv or "reports/tp_sl_efficiency/tp_sl_efficiency.csv"),
        by_symbol_csv=str(args.by_symbol_csv or "reports/trade_lifecycle_analysis/by_symbol.csv"),
        output_dir=str(args.output_dir or "reports/strategy_candidate_score"),
        shadow_sample_weight=float(args.shadow_sample_weight if args.shadow_sample_weight is not None else 0.3),
        observation_shadow_weight=float(args.observation_shadow_weight if args.observation_shadow_weight is not None else 0.1),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"strategy_count={result.get('strategy_count', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
