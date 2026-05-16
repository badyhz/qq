from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import find_bar_index, load_cached_klines, read_csv_rows, safe_ratio, to_epoch_ms, to_float_nan


FIELDS = [
    "experiment_candidate_id",
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "primary_horizon",
    "outcome",
    "first_touch",
    "mfe_r",
    "mae_r",
    "realized_r_multiple",
    "tp_was_touched",
    "sl_was_touched",
    "bars_to_exit",
    "evaluation_status",
    "missing_fields",
    "candidate_source",
    "next_run_candidate_id",
    "source_plan",
    "allowed_mode",
    "submit_permission",
]

BY_HORIZON_FIELDS = [
    "experiment_candidate_id",
    "experiment_id",
    "strategy_key",
    "candidate_source",
    "next_run_candidate_id",
    "horizon_bars",
    "is_primary_horizon",
    "outcome",
    "first_touch",
    "mfe_r",
    "mae_r",
    "realized_r_multiple",
    "evaluation_status",
]


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def _to_iso_utc(ts_ms: int) -> str:
    if ts_ms <= 0:
        return ""
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).isoformat()


def _default_levels(entry: float, side: str) -> tuple[float, float]:
    if not math.isfinite(entry) or entry <= 0:
        return float("nan"), float("nan")
    if side == "SHORT":
        return entry * 1.01, entry * 0.985
    return entry * 0.99, entry * 1.015


def _evaluate_horizon(
    *,
    side: str,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    risk_per_unit: float,
    future: list[dict[str, Any]],
) -> dict[str, Any]:
    if not future:
        return {
            "outcome": "INSUFFICIENT_DATA",
            "first_touch": "NONE",
            "mfe_r": float("nan"),
            "mae_r": float("nan"),
            "realized_r_multiple": float("nan"),
            "tp_was_touched": False,
            "sl_was_touched": False,
            "bars_to_exit": 0,
            "evaluation_status": "PARTIAL",
        }
    outcome = "UNKNOWN"
    first_touch = "NONE"
    tp_touched = False
    sl_touched = False
    exit_price = float("nan")
    bars_to_exit = len(future)
    for idx, bar in enumerate(future, start=1):
        high = to_float_nan(bar.get("high"))
        low = to_float_nan(bar.get("low"))
        if side == "SHORT":
            tp_hit = math.isfinite(tp_price) and math.isfinite(low) and low <= tp_price
            sl_hit = math.isfinite(sl_price) and math.isfinite(high) and high >= sl_price
        else:
            tp_hit = math.isfinite(tp_price) and math.isfinite(high) and high >= tp_price
            sl_hit = math.isfinite(sl_price) and math.isfinite(low) and low <= sl_price
        tp_touched = tp_touched or tp_hit
        sl_touched = sl_touched or sl_hit
        if not (tp_hit or sl_hit):
            continue
        bars_to_exit = idx
        if tp_hit and sl_hit:
            first_touch = "BOTH_SAME_BAR"
            outcome = "SHADOW_SL_FIRST"
            exit_price = sl_price
        elif tp_hit:
            first_touch = "TP"
            outcome = "SHADOW_TP_FIRST"
            exit_price = tp_price
        else:
            first_touch = "SL"
            outcome = "SHADOW_SL_FIRST"
            exit_price = sl_price
        break

    highs = [to_float_nan(row.get("high")) for row in future if math.isfinite(to_float_nan(row.get("high")))]
    lows = [to_float_nan(row.get("low")) for row in future if math.isfinite(to_float_nan(row.get("low")))]
    closes = [to_float_nan(row.get("close")) for row in future if math.isfinite(to_float_nan(row.get("close")))]
    final_close = closes[-1] if closes else float("nan")
    if outcome == "UNKNOWN":
        if math.isfinite(final_close) and math.isfinite(entry_price):
            pnl_per_unit = (final_close - entry_price) if side != "SHORT" else (entry_price - final_close)
            if pnl_per_unit > 1e-12:
                outcome = "SHADOW_TIMEOUT_PROFIT"
            elif pnl_per_unit < -1e-12:
                outcome = "SHADOW_TIMEOUT_LOSS"
            else:
                outcome = "SHADOW_TIMEOUT_FLAT"
            exit_price = final_close
        else:
            outcome = "INSUFFICIENT_DATA"
            first_touch = "UNKNOWN"

    mfe_per = float("nan")
    mae_per = float("nan")
    if math.isfinite(entry_price) and highs and lows:
        if side == "SHORT":
            mfe_per = entry_price - min(lows)
            mae_per = max(highs) - entry_price
        else:
            mfe_per = max(highs) - entry_price
            mae_per = entry_price - min(lows)
    realized_per = float("nan")
    if math.isfinite(entry_price) and math.isfinite(exit_price):
        realized_per = (exit_price - entry_price) if side != "SHORT" else (entry_price - exit_price)

    return {
        "outcome": outcome,
        "first_touch": first_touch,
        "mfe_r": safe_ratio(mfe_per, risk_per_unit),
        "mae_r": safe_ratio(mae_per, risk_per_unit),
        "realized_r_multiple": safe_ratio(realized_per, risk_per_unit),
        "tp_was_touched": bool(tp_touched),
        "sl_was_touched": bool(sl_touched),
        "bars_to_exit": bars_to_exit,
        "evaluation_status": "OK" if outcome not in {"INSUFFICIENT_DATA", "UNKNOWN"} else "PARTIAL",
    }


def evaluate_shadow_experiment_outcomes(
    *,
    experiment_candidates_csv: str = "reports/shadow_observation_experiment_runs/experiment_candidates.csv",
    include_next_run_candidates: bool = True,
    next_run_candidates_csv: str = "reports/next_shadow_experiment_run/next_run_candidates.csv",
    cache_dir: str = "data/cache/klines",
    output_dir: str = "reports/shadow_experiment_outcomes",
    horizons: str = "30,60,120",
    primary_horizon: int = 60,
) -> dict[str, Any]:
    default_experiment_csv = "reports/shadow_observation_experiment_runs/experiment_candidates.csv"
    default_next_run_csv = "reports/next_shadow_experiment_run/next_run_candidates.csv"
    experiment_candidates = read_csv_rows(Path(experiment_candidates_csv))
    next_run_candidates_path = Path(next_run_candidates_csv)
    if include_next_run_candidates and str(next_run_candidates_csv) == default_next_run_csv and str(experiment_candidates_csv) != default_experiment_csv:
        base_reports = Path(experiment_candidates_csv).resolve().parent.parent
        inferred = base_reports / "next_shadow_experiment_run" / "next_run_candidates.csv"
        next_run_candidates_path = inferred
    next_run_candidates = read_csv_rows(next_run_candidates_path) if include_next_run_candidates else []
    candidates: list[dict[str, Any]] = []
    for row in experiment_candidates:
        item = dict(row)
        item["_candidate_source"] = "experiment_candidates"
        item["_next_run_candidate_id"] = ""
        item["_source_plan"] = ""
        candidates.append(item)
    for row in next_run_candidates:
        item = dict(row)
        item["_candidate_source"] = "next_run_candidates"
        item["_next_run_candidate_id"] = str(row.get("next_run_candidate_id", "")).strip()
        item["_source_plan"] = str(row.get("source_plan", "")).strip()
        candidates.append(item)
    horizon_list = sorted({max(1, int(float(item.strip()))) for item in str(horizons or "30,60,120").split(",") if item.strip()})
    resolved_primary_horizon = int(primary_horizon or 60)
    if resolved_primary_horizon not in horizon_list:
        resolved_primary_horizon = horizon_list[0]

    rows: list[dict[str, Any]] = []
    by_horizon_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_source = str(candidate.get("_candidate_source", "experiment_candidates")).strip() or "experiment_candidates"
        next_run_candidate_id = str(candidate.get("_next_run_candidate_id", "")).strip()
        source_plan = str(candidate.get("_source_plan", "")).strip()
        cid = str(candidate.get("experiment_candidate_id", "")).strip()
        if not cid and next_run_candidate_id:
            cid = f"exp_from_{next_run_candidate_id}"
        exp_id = str(candidate.get("experiment_id", "")).strip()
        strategy_key = str(candidate.get("strategy_key", "")).strip()
        symbol = str(candidate.get("symbol", "")).strip().upper()
        side = _normalize_side(candidate.get("side"))
        timeframe = str(candidate.get("timeframe", "5m")).strip() or "5m"
        experiment_type = str(candidate.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN"
        signal_ms = to_epoch_ms(candidate.get("signal_time"))
        entry_price = to_float_nan(candidate.get("entry_price"))
        allowed_mode = str(candidate.get("allowed_mode", "SHADOW_ONLY")).strip().upper() or "SHADOW_ONLY"
        submit_permission = str(candidate.get("submit_permission", "NO_SUBMIT")).strip().upper() or "NO_SUBMIT"
        sl_price, tp_price = _default_levels(entry_price, side)
        risk_per_unit = abs(entry_price - sl_price) if (math.isfinite(entry_price) and math.isfinite(sl_price)) else float("nan")
        missing: list[str] = []
        klines = load_cached_klines(cache_root=cache_dir, symbol=symbol, timeframe=timeframe)
        if not klines:
            for h in horizon_list:
                by_horizon_rows.append(
                    {
                        "experiment_candidate_id": cid,
                        "experiment_id": exp_id,
                        "strategy_key": strategy_key,
                        "candidate_source": candidate_source,
                        "next_run_candidate_id": next_run_candidate_id,
                        "horizon_bars": h,
                        "is_primary_horizon": h == resolved_primary_horizon,
                        "outcome": "MISSING_KLINES",
                        "first_touch": "UNKNOWN",
                        "mfe_r": float("nan"),
                        "mae_r": float("nan"),
                        "realized_r_multiple": float("nan"),
                        "evaluation_status": "PARTIAL",
                    }
                )
            rows.append(
                {
                    "experiment_candidate_id": cid,
                    "experiment_id": exp_id,
                    "strategy_key": strategy_key,
                    "symbol": symbol,
                    "side": side,
                    "timeframe": timeframe,
                    "experiment_type": experiment_type,
                    "primary_horizon": resolved_primary_horizon,
                    "outcome": "MISSING_KLINES",
                    "first_touch": "UNKNOWN",
                    "mfe_r": float("nan"),
                    "mae_r": float("nan"),
                    "realized_r_multiple": float("nan"),
                    "tp_was_touched": False,
                    "sl_was_touched": False,
                    "bars_to_exit": 0,
                    "evaluation_status": "PARTIAL",
                    "missing_fields": "missing_klines",
                    "candidate_source": candidate_source,
                    "next_run_candidate_id": next_run_candidate_id,
                    "source_plan": source_plan,
                    "allowed_mode": allowed_mode,
                    "submit_permission": submit_permission,
                }
            )
            continue

        bar_index = find_bar_index(klines, signal_ms)
        if bar_index < 0:
            missing.append("signal_time_not_in_klines")
            for h in horizon_list:
                by_horizon_rows.append(
                    {
                        "experiment_candidate_id": cid,
                        "experiment_id": exp_id,
                        "strategy_key": strategy_key,
                        "candidate_source": candidate_source,
                        "next_run_candidate_id": next_run_candidate_id,
                        "horizon_bars": h,
                        "is_primary_horizon": h == resolved_primary_horizon,
                        "outcome": "INSUFFICIENT_DATA",
                        "first_touch": "UNKNOWN",
                        "mfe_r": float("nan"),
                        "mae_r": float("nan"),
                        "realized_r_multiple": float("nan"),
                        "evaluation_status": "PARTIAL",
                    }
                )
            rows.append(
                {
                    "experiment_candidate_id": cid,
                    "experiment_id": exp_id,
                    "strategy_key": strategy_key,
                    "symbol": symbol,
                    "side": side,
                    "timeframe": timeframe,
                    "experiment_type": experiment_type,
                    "primary_horizon": resolved_primary_horizon,
                    "outcome": "INSUFFICIENT_DATA",
                    "first_touch": "UNKNOWN",
                    "mfe_r": float("nan"),
                    "mae_r": float("nan"),
                    "realized_r_multiple": float("nan"),
                    "tp_was_touched": False,
                    "sl_was_touched": False,
                    "bars_to_exit": 0,
                    "evaluation_status": "PARTIAL",
                    "missing_fields": ";".join(missing),
                    "candidate_source": candidate_source,
                    "next_run_candidate_id": next_run_candidate_id,
                    "source_plan": source_plan,
                    "allowed_mode": allowed_mode,
                    "submit_permission": submit_permission,
                }
            )
            continue

        primary_metrics: dict[str, Any] | None = None
        for h in horizon_list:
            future = klines[bar_index + 1 : bar_index + 1 + h]
            metrics = _evaluate_horizon(
                side=side,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
                risk_per_unit=risk_per_unit,
                future=future,
            )
            by_horizon_rows.append(
                {
                    "experiment_candidate_id": cid,
                    "experiment_id": exp_id,
                    "strategy_key": strategy_key,
                    "candidate_source": candidate_source,
                    "next_run_candidate_id": next_run_candidate_id,
                    "horizon_bars": h,
                    "is_primary_horizon": h == resolved_primary_horizon,
                    "outcome": metrics.get("outcome", "UNKNOWN"),
                    "first_touch": metrics.get("first_touch", "UNKNOWN"),
                    "mfe_r": metrics.get("mfe_r", float("nan")),
                    "mae_r": metrics.get("mae_r", float("nan")),
                    "realized_r_multiple": metrics.get("realized_r_multiple", float("nan")),
                    "evaluation_status": metrics.get("evaluation_status", "PARTIAL"),
                }
            )
            if h == resolved_primary_horizon:
                primary_metrics = metrics

        primary_metrics = primary_metrics or _evaluate_horizon(
            side=side,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            risk_per_unit=risk_per_unit,
            future=[],
        )
        rows.append(
            {
                "experiment_candidate_id": cid,
                "experiment_id": exp_id,
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "experiment_type": experiment_type,
                "primary_horizon": resolved_primary_horizon,
                "outcome": primary_metrics.get("outcome", "UNKNOWN"),
                "first_touch": primary_metrics.get("first_touch", "UNKNOWN"),
                "mfe_r": primary_metrics.get("mfe_r", float("nan")),
                "mae_r": primary_metrics.get("mae_r", float("nan")),
                "realized_r_multiple": primary_metrics.get("realized_r_multiple", float("nan")),
                "tp_was_touched": bool(primary_metrics.get("tp_was_touched", False)),
                "sl_was_touched": bool(primary_metrics.get("sl_was_touched", False)),
                "bars_to_exit": int(primary_metrics.get("bars_to_exit", 0) or 0),
                "evaluation_status": primary_metrics.get("evaluation_status", "PARTIAL"),
                "missing_fields": ";".join(missing),
                "candidate_source": candidate_source,
                "next_run_candidate_id": next_run_candidate_id,
                "source_plan": source_plan,
                "allowed_mode": allowed_mode,
                "submit_permission": submit_permission,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiment_outcomes.csv"
    by_horizon_csv = out_dir / "experiment_outcomes_by_horizon.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})
    with by_horizon_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_HORIZON_FIELDS)
        writer.writeheader()
        for row in by_horizon_rows:
            writer.writerow({field: row.get(field, "") for field in BY_HORIZON_FIELDS})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if candidates else "PARTIAL",
        "candidate_count": len(candidates),
        "evaluated_count": len(rows),
        "candidate_sources": {
            "experiment_candidates": len(experiment_candidates),
            "next_run_candidates": len(next_run_candidates),
        },
        "next_run_candidate_count": len(next_run_candidates),
        "next_run_evaluated_count": sum(
            1 for row in rows if str(row.get("candidate_source", "")).strip() == "next_run_candidates"
        ),
        "tp_first_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_TP_FIRST"),
        "sl_first_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_SL_FIRST"),
        "timeout_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper().startswith("SHADOW_TIMEOUT_")),
        "missing_klines_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "MISSING_KLINES"),
        "horizons": horizon_list,
        "primary_horizon": resolved_primary_horizon,
        "csv_path": str(csv_path),
        "by_horizon_csv": str(by_horizon_csv),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    if len(candidates) == 0:
        summary["reason"] = "no_experiment_candidates"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Outcomes",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- candidate_count: {summary['candidate_count']}",
        f"- evaluated_count: {summary['evaluated_count']}",
        f"- tp_first_count: {summary['tp_first_count']}",
        f"- sl_first_count: {summary['sl_first_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate outcomes for shadow observation experiment candidates")
    parser.add_argument("--experiment-candidates-csv", default="reports/shadow_observation_experiment_runs/experiment_candidates.csv")
    parser.add_argument("--include-next-run-candidates", dest="include_next_run_candidates", action="store_true")
    parser.add_argument("--no-include-next-run-candidates", dest="include_next_run_candidates", action="store_false")
    parser.set_defaults(include_next_run_candidates=True)
    parser.add_argument("--next-run-candidates-csv", default="reports/next_shadow_experiment_run/next_run_candidates.csv")
    parser.add_argument("--cache-dir", default="data/cache/klines")
    parser.add_argument("--output-dir", default="reports/shadow_experiment_outcomes")
    parser.add_argument("--horizons", default="30,60,120")
    parser.add_argument("--primary-horizon", type=int, default=60)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_shadow_experiment_outcomes(
        experiment_candidates_csv=str(
            args.experiment_candidates_csv or "reports/shadow_observation_experiment_runs/experiment_candidates.csv"
        ),
        include_next_run_candidates=bool(args.include_next_run_candidates),
        next_run_candidates_csv=str(args.next_run_candidates_csv or "reports/next_shadow_experiment_run/next_run_candidates.csv"),
        cache_dir=str(args.cache_dir or "data/cache/klines"),
        output_dir=str(args.output_dir or "reports/shadow_experiment_outcomes"),
        horizons=str(args.horizons or "30,60,120"),
        primary_horizon=int(args.primary_horizon or 60),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"evaluated_count={result.get('evaluated_count', 0)}")


if __name__ == "__main__":
    main()
