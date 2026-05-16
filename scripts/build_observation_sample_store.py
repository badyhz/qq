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
    "observation_sample_id",
    "shadow_candidate_id",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "collector_mode",
    "candidate_source",
    "near_miss",
    "near_miss_reason",
    "signal_strength_score",
    "trend_score",
    "breakout_score",
    "risk_reward_score",
    "primary_horizon_outcome",
    "primary_horizon_realized_r",
    "best_horizon_bars",
    "best_horizon_realized_r",
    "best_horizon_outcome",
    "horizon_consistency_score",
    "near_miss_quality_score",
    "near_miss_verdict",
    "near_miss_promotion_hint",
    "sample_status",
    "sample_weight",
    "sample_origin",
    "experiment_id",
    "experiment_type",
    "experiment_candidate_id",
    "experiment_status",
    "experiment_outcome",
    "experiment_primary_horizon",
    "experiment_realized_r_multiple",
    "experiment_best_horizon_bars",
    "experiment_best_horizon_realized_r",
    "experiment_evaluation_status",
    "created_at",
    "source_reports",
]


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_round(value: float) -> float:
    if not math.isfinite(value):
        return float("nan")
    return round(value, 8)


def _sample_status(*, outcome: str, near_miss_verdict: str) -> str:
    out = str(outcome or "").strip().upper()
    verdict = str(near_miss_verdict or "").strip().upper()
    if out in {"", "NO_OUTCOME", "UNKNOWN"}:
        return "OBSERVATION_PENDING_OUTCOME"
    if out in {"MISSING_KLINES", "INSUFFICIENT_DATA"}:
        return "OBSERVATION_INSUFFICIENT_DATA"
    if verdict == "IGNORE":
        return "OBSERVATION_REJECTED"
    return "OBSERVATION_EVALUATED"


def build_observation_sample_store(
    *,
    shadow_universe_candidates_csv: str = "reports/shadow_universe_collection/shadow_universe_candidates.csv",
    near_miss_scores_csv: str = "reports/shadow_near_miss/near_miss_scores.csv",
    shadow_outcomes_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv",
    shadow_outcomes_by_horizon_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv",
    by_collector_mode_csv: str = "reports/shadow_sample_quality/by_collector_mode.csv",
    by_horizon_csv: str = "reports/shadow_sample_quality/by_horizon.csv",
    experiment_candidates_csv: str = "reports/shadow_observation_experiment_runs/experiment_candidates.csv",
    experiment_outcomes_csv: str = "reports/shadow_experiment_outcomes/experiment_outcomes.csv",
    experiment_outcomes_by_horizon_csv: str = "reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv",
    output_dir: str = "reports/observation_sample_store",
) -> dict[str, Any]:
    default_experiment_candidates = "reports/shadow_observation_experiment_runs/experiment_candidates.csv"
    default_experiment_outcomes = "reports/shadow_experiment_outcomes/experiment_outcomes.csv"
    default_experiment_outcomes_by_horizon = "reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv"
    report_root = Path(shadow_universe_candidates_csv).resolve().parent.parent
    if str(experiment_candidates_csv) == default_experiment_candidates:
        experiment_candidates_csv = str(report_root / "shadow_observation_experiment_runs" / "experiment_candidates.csv")
    if str(experiment_outcomes_csv) == default_experiment_outcomes:
        experiment_outcomes_csv = str(report_root / "shadow_experiment_outcomes" / "experiment_outcomes.csv")
    if str(experiment_outcomes_by_horizon_csv) == default_experiment_outcomes_by_horizon:
        experiment_outcomes_by_horizon_csv = str(
            report_root / "shadow_experiment_outcomes" / "experiment_outcomes_by_horizon.csv"
        )

    universe_rows = read_csv_rows(Path(shadow_universe_candidates_csv))
    near_rows = read_csv_rows(Path(near_miss_scores_csv))
    outcome_rows = read_csv_rows(Path(shadow_outcomes_csv))
    by_horizon_rows = read_csv_rows(Path(shadow_outcomes_by_horizon_csv))
    experiment_candidate_rows = read_csv_rows(Path(experiment_candidates_csv))
    experiment_outcome_rows = read_csv_rows(Path(experiment_outcomes_csv))
    experiment_outcome_horizon_rows = read_csv_rows(Path(experiment_outcomes_by_horizon_csv))
    _ = read_csv_rows(Path(by_collector_mode_csv))
    _ = read_csv_rows(Path(by_horizon_csv))

    candidate_index: dict[str, dict[str, Any]] = {}
    for row in universe_rows:
        cid = str(row.get("candidate_id", row.get("shadow_candidate_id", ""))).strip()
        if cid:
            candidate_index[cid] = row

    near_index: dict[str, dict[str, Any]] = {}
    for row in near_rows:
        cid = str(row.get("shadow_candidate_id", "")).strip()
        if cid:
            near_index[cid] = row

    outcome_index: dict[str, dict[str, Any]] = {}
    for row in outcome_rows:
        cid = str(row.get("shadow_candidate_id", "")).strip()
        if cid:
            outcome_index[cid] = row

    best_horizon_index: dict[str, dict[str, Any]] = {}
    for row in by_horizon_rows:
        cid = str(row.get("shadow_candidate_id", "")).strip()
        if not cid:
            continue
        realized = to_float_nan(row.get("realized_r_multiple"))
        old = best_horizon_index.get(cid)
        old_realized = to_float_nan((old or {}).get("realized_r_multiple"))
        if old is None:
            best_horizon_index[cid] = row
            continue
        if math.isfinite(realized) and ((not math.isfinite(old_realized)) or realized > old_realized):
            best_horizon_index[cid] = row

    sample_ids = sorted(set(candidate_index.keys()) | set(near_index.keys()) | set(outcome_index.keys()))

    experiment_candidate_index: dict[str, dict[str, Any]] = {}
    for row in experiment_candidate_rows:
        cid = str(row.get("experiment_candidate_id", "")).strip()
        if cid:
            experiment_candidate_index[cid] = row
    experiment_outcome_index: dict[str, dict[str, Any]] = {}
    for row in experiment_outcome_rows:
        cid = str(row.get("experiment_candidate_id", "")).strip()
        if cid:
            experiment_outcome_index[cid] = row
    experiment_best_horizon_index: dict[str, dict[str, Any]] = {}
    for row in experiment_outcome_horizon_rows:
        cid = str(row.get("experiment_candidate_id", "")).strip()
        if not cid:
            continue
        realized = to_float_nan(row.get("realized_r_multiple"))
        old = experiment_best_horizon_index.get(cid)
        old_realized = to_float_nan((old or {}).get("realized_r_multiple"))
        if old is None:
            experiment_best_horizon_index[cid] = row
            continue
        if math.isfinite(realized) and ((not math.isfinite(old_realized)) or realized > old_realized):
            experiment_best_horizon_index[cid] = row

    now_iso = datetime.now(timezone.utc).isoformat()
    out_rows: list[dict[str, Any]] = []
    seen_shadow_candidate_ids: set[str] = set()
    seen_experiment_candidate_ids: set[str] = set()
    for cid in sample_ids:
        candidate = candidate_index.get(cid, {})
        near = near_index.get(cid, {})
        outcome = outcome_index.get(cid, {})
        best_horizon = best_horizon_index.get(cid, {})
        collector_mode = str(
            candidate.get("collector_mode", near.get("collector_mode", outcome.get("collector_mode", "observation")))
        ).strip().lower() or "observation"
        near_miss = _to_bool(candidate.get("near_miss")) or _to_bool(near.get("near_miss")) or collector_mode == "observation"
        near_reason = str(candidate.get("near_miss_reason", near.get("near_miss_reason", ""))).strip()
        signal_strength = to_float_nan(candidate.get("signal_strength_score", near.get("signal_strength_score")))
        trend_score = to_float_nan(candidate.get("trend_score", near.get("trend_score")))
        breakout_score = to_float_nan(candidate.get("breakout_score", near.get("breakout_score")))
        risk_reward_score = to_float_nan(candidate.get("risk_reward_score", near.get("risk_reward_score")))
        primary_outcome = str(
            near.get("primary_horizon_outcome", outcome.get("outcome", "NO_OUTCOME"))
        ).strip().upper() or "NO_OUTCOME"
        primary_r = to_float_nan(near.get("primary_horizon_realized_r", outcome.get("realized_r_multiple")))
        best_h = to_float_nan(near.get("best_horizon_bars", best_horizon.get("horizon_bars")))
        best_h_r = to_float_nan(near.get("best_horizon_realized_r", best_horizon.get("realized_r_multiple")))
        best_h_outcome = str(
            near.get("best_horizon_outcome", best_horizon.get("outcome", primary_outcome))
        ).strip().upper() or primary_outcome
        consistency = to_float_nan(near.get("horizon_consistency_score"))
        near_score = to_float_nan(near.get("near_miss_quality_score"))
        near_verdict = str(near.get("near_miss_verdict", "NO_OUTCOME")).strip().upper() or "NO_OUTCOME"
        near_hint = str(near.get("near_miss_promotion_hint", "WATCH_MORE")).strip().upper() or "WATCH_MORE"
        status = _sample_status(outcome=primary_outcome, near_miss_verdict=near_verdict)
        sample_weight = 0.1 if (near_miss or collector_mode == "observation") else 0.3
        source_reports = sorted(
            {
                "shadow_universe_collection",
                "shadow_near_miss",
                "shadow_candidate_outcomes",
                "shadow_candidate_outcomes_by_horizon",
            }
        )
        if cid in seen_shadow_candidate_ids:
            continue
        seen_shadow_candidate_ids.add(cid)
        out_rows.append(
            {
                "observation_sample_id": f"obs_{cid}",
                "shadow_candidate_id": cid,
                "symbol": str(candidate.get("symbol", near.get("symbol", outcome.get("symbol", "")))).strip().upper(),
                "side": str(candidate.get("side", near.get("side", outcome.get("side", "")))).strip().upper(),
                "timeframe": str(candidate.get("timeframe", near.get("timeframe", outcome.get("timeframe", "5m")))).strip() or "5m",
                "strategy_key": str(
                    candidate.get("strategy_key", near.get("strategy_key", outcome.get("strategy_key", "")))
                ).strip(),
                "collector_mode": collector_mode,
                "candidate_source": str(outcome.get("candidate_source", "shadow_universe_collection")).strip()
                or "shadow_universe_collection",
                "near_miss": bool(near_miss),
                "near_miss_reason": near_reason,
                "signal_strength_score": _safe_round(signal_strength),
                "trend_score": _safe_round(trend_score),
                "breakout_score": _safe_round(breakout_score),
                "risk_reward_score": _safe_round(risk_reward_score),
                "primary_horizon_outcome": primary_outcome,
                "primary_horizon_realized_r": _safe_round(primary_r),
                "best_horizon_bars": int(best_h) if math.isfinite(best_h) else float("nan"),
                "best_horizon_realized_r": _safe_round(best_h_r),
                "best_horizon_outcome": best_h_outcome,
                "horizon_consistency_score": _safe_round(consistency),
                "near_miss_quality_score": _safe_round(near_score),
                "near_miss_verdict": near_verdict,
                "near_miss_promotion_hint": near_hint,
                "sample_status": status,
                "sample_weight": sample_weight,
                "sample_origin": "NEAR_MISS" if bool(near_miss) else ("SHADOW_OBSERVATION" if collector_mode == "observation" else "UNKNOWN"),
                "experiment_id": "",
                "experiment_type": "",
                "experiment_candidate_id": "",
                "experiment_status": "",
                "experiment_outcome": "",
                "experiment_primary_horizon": float("nan"),
                "experiment_realized_r_multiple": float("nan"),
                "experiment_best_horizon_bars": float("nan"),
                "experiment_best_horizon_realized_r": float("nan"),
                "experiment_evaluation_status": "",
                "created_at": now_iso,
                "source_reports": ";".join(source_reports),
            }
        )

    for exp_cid in sorted(experiment_candidate_index.keys()):
        if exp_cid in seen_experiment_candidate_ids:
            continue
        seen_experiment_candidate_ids.add(exp_cid)
        exp = experiment_candidate_index.get(exp_cid, {})
        out = experiment_outcome_index.get(exp_cid, {})
        best_h = experiment_best_horizon_index.get(exp_cid, {})
        exp_outcome = str(out.get("outcome", "NO_OUTCOME")).strip().upper() or "NO_OUTCOME"
        exp_eval_status = str(out.get("evaluation_status", "PARTIAL")).strip().upper() or "PARTIAL"
        best_h_bars = to_float_nan(best_h.get("horizon_bars"))
        best_h_realized = to_float_nan(best_h.get("realized_r_multiple"))
        primary_horizon = to_float_nan(out.get("primary_horizon"))
        sample_status = "OBSERVATION_EVALUATED"
        if exp_outcome in {"NO_OUTCOME", "UNKNOWN"}:
            sample_status = "OBSERVATION_PENDING_OUTCOME"
        elif exp_outcome in {"MISSING_KLINES", "INSUFFICIENT_DATA"}:
            sample_status = "OBSERVATION_INSUFFICIENT_DATA"
        out_rows.append(
            {
                "observation_sample_id": f"obs_exp_{exp_cid}",
                "shadow_candidate_id": "",
                "symbol": str(exp.get("symbol", out.get("symbol", ""))).strip().upper(),
                "side": str(exp.get("side", out.get("side", ""))).strip().upper(),
                "timeframe": str(exp.get("timeframe", out.get("timeframe", "5m"))).strip() or "5m",
                "strategy_key": str(exp.get("strategy_key", out.get("strategy_key", ""))).strip(),
                "collector_mode": str(exp.get("collector_mode", "observation")).strip().lower() or "observation",
                "candidate_source": "shadow_observation_experiment_runs",
                "near_miss": _to_bool(exp.get("near_miss")),
                "near_miss_reason": "",
                "signal_strength_score": _safe_round(to_float_nan(exp.get("signal_strength_score"))),
                "trend_score": _safe_round(to_float_nan(exp.get("trend_score"))),
                "breakout_score": _safe_round(to_float_nan(exp.get("breakout_score"))),
                "risk_reward_score": _safe_round(to_float_nan(exp.get("risk_reward_score"))),
                "primary_horizon_outcome": exp_outcome,
                "primary_horizon_realized_r": _safe_round(to_float_nan(out.get("realized_r_multiple"))),
                "best_horizon_bars": int(best_h_bars) if math.isfinite(best_h_bars) else float("nan"),
                "best_horizon_realized_r": _safe_round(best_h_realized),
                "best_horizon_outcome": str(best_h.get("outcome", exp_outcome)).strip().upper() or exp_outcome,
                "horizon_consistency_score": float("nan"),
                "near_miss_quality_score": float("nan"),
                "near_miss_verdict": "NO_OUTCOME",
                "near_miss_promotion_hint": "WATCH_MORE",
                "sample_status": sample_status,
                "sample_weight": 0.1,
                "sample_origin": "SHADOW_EXPERIMENT",
                "experiment_id": str(exp.get("experiment_id", out.get("experiment_id", ""))).strip(),
                "experiment_type": str(exp.get("experiment_type", out.get("experiment_type", "UNKNOWN"))).strip().upper() or "UNKNOWN",
                "experiment_candidate_id": exp_cid,
                "experiment_status": "OBSERVATION",
                "experiment_outcome": exp_outcome,
                "experiment_primary_horizon": int(primary_horizon) if math.isfinite(primary_horizon) else float("nan"),
                "experiment_realized_r_multiple": _safe_round(to_float_nan(out.get("realized_r_multiple"))),
                "experiment_best_horizon_bars": int(best_h_bars) if math.isfinite(best_h_bars) else float("nan"),
                "experiment_best_horizon_realized_r": _safe_round(best_h_realized),
                "experiment_evaluation_status": exp_eval_status,
                "created_at": now_iso,
                "source_reports": "shadow_observation_experiment_runs;shadow_experiment_outcomes;shadow_experiment_outcomes_by_horizon",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "observation_samples.csv"
    summary_json_path = out_dir / "summary.json"
    summary_md_path = out_dir / "summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": now_iso,
        "final_verdict": "PASS" if out_rows else "PARTIAL",
        "observation_count": len(out_rows),
        "near_miss_count": sum(1 for row in out_rows if _to_bool(row.get("near_miss"))),
        "experiment_sample_count": sum(
            1 for row in out_rows if str(row.get("sample_origin", "")).strip().upper() == "SHADOW_EXPERIMENT"
        ),
        "evaluated_count": sum(1 for row in out_rows if str(row.get("sample_status", "")).strip().upper() == "OBSERVATION_EVALUATED"),
        "pending_outcome_count": sum(
            1
            for row in out_rows
            if str(row.get("sample_status", "")).strip().upper() in {"OBSERVATION_PENDING_OUTCOME", "OBSERVATION_INSUFFICIENT_DATA"}
        ),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json_path),
        "summary_md": str(summary_md_path),
    }
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Observation Sample Store",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- observation_count: {summary['observation_count']}",
        f"- near_miss_count: {summary['near_miss_count']}",
        f"- experiment_sample_count: {summary['experiment_sample_count']}",
        f"- evaluated_count: {summary['evaluated_count']}",
        f"- pending_outcome_count: {summary['pending_outcome_count']}",
    ]
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build unified observation sample store from near-miss/shadow reports")
    parser.add_argument("--shadow-universe-candidates-csv", default="reports/shadow_universe_collection/shadow_universe_candidates.csv")
    parser.add_argument("--near-miss-scores-csv", default="reports/shadow_near_miss/near_miss_scores.csv")
    parser.add_argument("--shadow-outcomes-csv", default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv")
    parser.add_argument(
        "--shadow-outcomes-by-horizon-csv",
        default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv",
    )
    parser.add_argument("--by-collector-mode-csv", default="reports/shadow_sample_quality/by_collector_mode.csv")
    parser.add_argument("--by-horizon-csv", default="reports/shadow_sample_quality/by_horizon.csv")
    parser.add_argument("--experiment-candidates-csv", default="reports/shadow_observation_experiment_runs/experiment_candidates.csv")
    parser.add_argument("--experiment-outcomes-csv", default="reports/shadow_experiment_outcomes/experiment_outcomes.csv")
    parser.add_argument(
        "--experiment-outcomes-by-horizon-csv",
        default="reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv",
    )
    parser.add_argument("--output-dir", default="reports/observation_sample_store")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = build_observation_sample_store(
        shadow_universe_candidates_csv=str(args.shadow_universe_candidates_csv or "reports/shadow_universe_collection/shadow_universe_candidates.csv"),
        near_miss_scores_csv=str(args.near_miss_scores_csv or "reports/shadow_near_miss/near_miss_scores.csv"),
        shadow_outcomes_csv=str(args.shadow_outcomes_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv"),
        shadow_outcomes_by_horizon_csv=str(
            args.shadow_outcomes_by_horizon_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv"
        ),
        by_collector_mode_csv=str(args.by_collector_mode_csv or "reports/shadow_sample_quality/by_collector_mode.csv"),
        by_horizon_csv=str(args.by_horizon_csv or "reports/shadow_sample_quality/by_horizon.csv"),
        experiment_candidates_csv=str(
            args.experiment_candidates_csv or "reports/shadow_observation_experiment_runs/experiment_candidates.csv"
        ),
        experiment_outcomes_csv=str(
            args.experiment_outcomes_csv or "reports/shadow_experiment_outcomes/experiment_outcomes.csv"
        ),
        experiment_outcomes_by_horizon_csv=str(
            args.experiment_outcomes_by_horizon_csv or "reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv"
        ),
        output_dir=str(args.output_dir or "reports/observation_sample_store"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"observation_count={result.get('observation_count', 0)}")


if __name__ == "__main__":
    main()
