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
    "shadow_candidate_id",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "collector_mode",
    "near_miss",
    "near_miss_reason",
    "signal_strength_score",
    "trend_score",
    "breakout_score",
    "risk_reward_score",
    "outcome",
    "best_horizon_bars",
    "best_horizon_realized_r",
    "best_horizon_outcome",
    "primary_horizon_outcome",
    "primary_horizon_mfe_r",
    "primary_horizon_mae_r",
    "horizon_consistency_score",
    "primary_horizon_realized_r",
    "near_miss_quality_score",
    "near_miss_verdict",
    "near_miss_promotion_hint",
    "reason",
]


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def score_shadow_near_miss_samples(
    *,
    shadow_candidates_csv: str = "reports/shadow_candidate_collection/shadow_candidates.csv",
    shadow_universe_candidates_csv: str = "reports/shadow_universe_collection/shadow_universe_candidates.csv",
    shadow_outcomes_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv",
    shadow_outcomes_by_horizon_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv",
    output_dir: str = "reports/shadow_near_miss",
) -> dict[str, Any]:
    candidate_rows = read_csv_rows(Path(shadow_candidates_csv))
    universe_rows = read_csv_rows(Path(shadow_universe_candidates_csv))
    outcome_rows = read_csv_rows(Path(shadow_outcomes_csv))
    by_horizon_rows = read_csv_rows(Path(shadow_outcomes_by_horizon_csv))

    candidates: dict[str, dict[str, Any]] = {}
    for row in candidate_rows + universe_rows:
        cid = str(row.get("candidate_id", row.get("shadow_candidate_id", ""))).strip()
        if not cid:
            continue
        candidates[cid] = {**candidates.get(cid, {}), **row}

    outcome_index = {
        str(row.get("shadow_candidate_id", "")).strip(): row
        for row in outcome_rows
        if str(row.get("shadow_candidate_id", "")).strip()
    }
    primary_by_id: dict[str, dict[str, Any]] = {}
    horizons_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in by_horizon_rows:
        cid = str(row.get("shadow_candidate_id", "")).strip()
        if not cid:
            continue
        horizons_by_id.setdefault(cid, []).append(row)
        if _to_bool(row.get("is_primary_horizon")):
            primary_by_id[cid] = row

    out_rows: list[dict[str, Any]] = []
    for cid, row in sorted(candidates.items()):
        near_miss = _to_bool(row.get("near_miss")) or str(row.get("candidate_status", "")).strip().upper() == "SHADOW_OBSERVATION_ONLY"
        if not near_miss:
            continue
        outcome = outcome_index.get(cid, {})
        primary = primary_by_id.get(cid, {})
        signal_strength = to_float_nan(row.get("signal_strength_score"))
        trend_score = to_float_nan(row.get("trend_score"))
        breakout_score = to_float_nan(row.get("breakout_score"))
        risk_reward_score = to_float_nan(row.get("risk_reward_score"))
        primary_r = to_float_nan(primary.get("realized_r_multiple"))
        if not math.isfinite(primary_r):
            primary_r = to_float_nan(outcome.get("realized_r_multiple"))
        mfe_r = to_float_nan(primary.get("mfe_r"))
        mae_r = to_float_nan(primary.get("mae_r"))
        primary_outcome = str(primary.get("outcome", "")).strip().upper() or str(outcome.get("outcome", "")).strip().upper() or "NO_OUTCOME"

        horizon_rows = list(horizons_by_id.get(cid, []))
        best_horizon_bars = float("nan")
        best_horizon_realized_r = float("nan")
        best_horizon_outcome = "UNKNOWN"
        consistency_score = float("nan")
        if horizon_rows:
            ranked = sorted(
                horizon_rows,
                key=lambda r: to_float_nan(r.get("realized_r_multiple")) if math.isfinite(to_float_nan(r.get("realized_r_multiple"))) else -1e18,
                reverse=True,
            )
            top = ranked[0]
            best_horizon_bars = to_float_nan(top.get("horizon_bars"))
            best_horizon_realized_r = to_float_nan(top.get("realized_r_multiple"))
            best_horizon_outcome = str(top.get("outcome", "")).strip().upper() or "UNKNOWN"
            r_values = [to_float_nan(r.get("realized_r_multiple")) for r in horizon_rows if math.isfinite(to_float_nan(r.get("realized_r_multiple")))]
            if r_values:
                pos = sum(1 for x in r_values if x > 0)
                neg = sum(1 for x in r_values if x < 0)
                total = len(r_values)
                consistency_score = max(pos, neg) / max(1, total) * 100.0

        signal_component = max(0.0, min(100.0, signal_strength if math.isfinite(signal_strength) else 0.0))
        r_component = max(0.0, min(100.0, 50.0 + (primary_r * 50.0))) if math.isfinite(primary_r) else 0.0
        rr_component = max(0.0, min(100.0, risk_reward_score if math.isfinite(risk_reward_score) else 0.0))
        structure_component = 0.0
        if math.isfinite(mfe_r) and math.isfinite(mae_r):
            ratio = mfe_r / max(0.1, mae_r)
            structure_component = max(0.0, min(100.0, ratio * 40.0))
        near_miss_score = (signal_component * 0.4) + (r_component * 0.3) + (rr_component * 0.2) + (structure_component * 0.1)
        near_miss_score = max(0.0, min(100.0, near_miss_score))

        verdict = "NO_OUTCOME"
        promotion_hint = "UNKNOWN"
        reasons: list[str] = []
        if not outcome:
            verdict = "NO_OUTCOME"
            promotion_hint = "WATCH_MORE"
            reasons.append("missing_outcome")
        else:
            if near_miss_score >= 75.0 and math.isfinite(primary_r) and primary_r > 0:
                verdict = "PROMISING"
                reasons.append("high_score_positive_outcome")
            elif near_miss_score >= 50.0:
                verdict = "WATCH"
                reasons.append("mid_score")
            else:
                verdict = "IGNORE"
                reasons.append("low_score")
            if not math.isfinite(primary_r):
                verdict = "NO_OUTCOME"
                promotion_hint = "WATCH_MORE"
                reasons.append("primary_horizon_realized_r_missing")

        reason_text = str(row.get("near_miss_reason", "")).strip().lower()
        if promotion_hint == "UNKNOWN":
            if verdict in {"NO_OUTCOME"} or (not math.isfinite(best_horizon_realized_r)):
                promotion_hint = "WATCH_MORE"
            elif math.isfinite(best_horizon_realized_r) and best_horizon_realized_r <= 0:
                promotion_hint = "KEEP_STRICT_RULES" if near_miss_score >= 50 else "IGNORE"
            elif "breakout" in reason_text and math.isfinite(best_horizon_realized_r) and best_horizon_realized_r > 0 and math.isfinite(mfe_r) and mfe_r > 1:
                promotion_hint = "RELAX_BREAKOUT_FILTER"
            elif "trend" in reason_text and math.isfinite(best_horizon_realized_r) and best_horizon_realized_r > 0:
                promotion_hint = "RELAX_TREND_FILTER"
            elif "risk_reward" in reason_text and math.isfinite(best_horizon_realized_r) and best_horizon_realized_r > 0:
                promotion_hint = "RELAX_RISK_REWARD_FILTER"
            elif verdict in {"WATCH", "PROMISING"}:
                promotion_hint = "WATCH_MORE"
            else:
                promotion_hint = "KEEP_STRICT_RULES"

        out_rows.append(
            {
                "shadow_candidate_id": cid,
                "symbol": str(row.get("symbol", "")).strip().upper(),
                "side": str(row.get("side", "")).strip().upper(),
                "timeframe": str(row.get("timeframe", "5m")).strip() or "5m",
                "strategy_key": str(row.get("strategy_key", "")).strip(),
                "collector_mode": str(row.get("collector_mode", "")).strip().lower() or "unknown",
                "near_miss": bool(near_miss),
                "near_miss_reason": str(row.get("near_miss_reason", "")).strip(),
                "signal_strength_score": round(signal_strength, 8) if math.isfinite(signal_strength) else float("nan"),
                "trend_score": round(trend_score, 8) if math.isfinite(trend_score) else float("nan"),
                "breakout_score": round(breakout_score, 8) if math.isfinite(breakout_score) else float("nan"),
                "risk_reward_score": round(risk_reward_score, 8) if math.isfinite(risk_reward_score) else float("nan"),
                "outcome": str(outcome.get("outcome", "")).strip().upper() or "NO_OUTCOME",
                "best_horizon_bars": int(best_horizon_bars) if math.isfinite(best_horizon_bars) else float("nan"),
                "best_horizon_realized_r": round(best_horizon_realized_r, 8) if math.isfinite(best_horizon_realized_r) else float("nan"),
                "best_horizon_outcome": best_horizon_outcome,
                "primary_horizon_outcome": primary_outcome,
                "primary_horizon_mfe_r": round(mfe_r, 8) if math.isfinite(mfe_r) else float("nan"),
                "primary_horizon_mae_r": round(mae_r, 8) if math.isfinite(mae_r) else float("nan"),
                "horizon_consistency_score": round(consistency_score, 8) if math.isfinite(consistency_score) else float("nan"),
                "primary_horizon_realized_r": round(primary_r, 8) if math.isfinite(primary_r) else float("nan"),
                "near_miss_quality_score": round(near_miss_score, 8),
                "near_miss_verdict": verdict,
                "near_miss_promotion_hint": promotion_hint,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "near_miss_scores.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if out_rows else "PARTIAL",
        "candidate_count": len(out_rows),
        "promising_count": sum(1 for row in out_rows if str(row.get("near_miss_verdict", "")).strip().upper() == "PROMISING"),
        "watch_count": sum(1 for row in out_rows if str(row.get("near_miss_verdict", "")).strip().upper() == "WATCH"),
        "ignore_count": sum(1 for row in out_rows if str(row.get("near_miss_verdict", "")).strip().upper() == "IGNORE"),
        "no_outcome_count": sum(1 for row in out_rows if str(row.get("near_miss_verdict", "")).strip().upper() == "NO_OUTCOME"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Near-Miss Scores",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- candidate_count: {summary['candidate_count']}",
        f"- promising_count: {summary['promising_count']}",
        f"- watch_count: {summary['watch_count']}",
        f"- ignore_count: {summary['ignore_count']}",
        f"- no_outcome_count: {summary['no_outcome_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score near-miss shadow samples separately")
    parser.add_argument("--shadow-candidates-csv", default="reports/shadow_candidate_collection/shadow_candidates.csv")
    parser.add_argument("--shadow-universe-candidates-csv", default="reports/shadow_universe_collection/shadow_universe_candidates.csv")
    parser.add_argument("--shadow-outcomes-csv", default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv")
    parser.add_argument("--shadow-outcomes-by-horizon-csv", default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv")
    parser.add_argument("--output-dir", default="reports/shadow_near_miss")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = score_shadow_near_miss_samples(
        shadow_candidates_csv=str(args.shadow_candidates_csv or "reports/shadow_candidate_collection/shadow_candidates.csv"),
        shadow_universe_candidates_csv=str(args.shadow_universe_candidates_csv or "reports/shadow_universe_collection/shadow_universe_candidates.csv"),
        shadow_outcomes_csv=str(args.shadow_outcomes_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv"),
        shadow_outcomes_by_horizon_csv=str(
            args.shadow_outcomes_by_horizon_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv"
        ),
        output_dir=str(args.output_dir or "reports/shadow_near_miss"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"candidate_count={result.get('candidate_count', 0)}")


if __name__ == "__main__":
    main()
