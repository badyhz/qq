from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows


FIELDS = [
    "suggestion_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "suggestion_type",
    "current_threshold",
    "suggested_threshold",
    "expected_effect",
    "risk_level",
    "confidence_level",
    "supporting_sample_count",
    "supporting_observation_ids",
    "linked_experiment_count",
    "linked_experiment_candidate_count",
    "linked_experiment_evaluated_count",
    "best_experiment_type",
    "best_experiment_realized_r",
    "experiment_support_status",
    "updated_suggestion_verdict",
    "suggestion_verdict",
    "reason",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _map_gap_to_suggestion(value: str) -> str:
    text = str(value or "").strip().upper()
    mapping = {
        "RELAX_TREND_SCORE": "RELAX_MIN_TREND_SCORE",
        "RELAX_BREAKOUT_SCORE": "RELAX_MIN_BREAKOUT_SCORE",
        "RELAX_RISK_REWARD": "RELAX_MIN_RISK_REWARD",
        "RELAX_NEAR_MISS_THRESHOLD": "RELAX_NEAR_MISS_THRESHOLD",
        "KEEP_STRICT": "KEEP_STRICT",
    }
    return mapping.get(text, "NO_CHANGE")


def _threshold_pair(suggestion_type: str) -> tuple[str, str]:
    table = {
        "RELAX_MIN_TREND_SCORE": ("60", "55"),
        "RELAX_MIN_BREAKOUT_SCORE": ("60", "55"),
        "RELAX_MIN_RISK_REWARD": ("1.0", "0.9"),
        "RELAX_NEAR_MISS_THRESHOLD": ("0.80", "0.75"),
        "KEEP_STRICT": ("strict", "strict"),
        "NO_CHANGE": ("strict", "strict"),
    }
    return table.get(suggestion_type, ("strict", "strict"))


def generate_strategy_relaxation_suggestions(
    *,
    near_miss_strict_gap_csv: str = "reports/near_miss_strict_gap/near_miss_strict_gap.csv",
    observation_samples_csv: str = "reports/observation_sample_store/observation_samples.csv",
    near_miss_scores_csv: str = "reports/shadow_near_miss/near_miss_scores.csv",
    shadow_quality_dashboard_json: str = "reports/shadow_sample_quality/shadow_sample_quality_dashboard.json",
    shadow_experiment_comparison_csv: str = "reports/shadow_experiment_comparison/experiment_comparison.csv",
    shadow_experiment_promotion_csv: str = "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    shadow_experiment_outcomes_csv: str = "reports/shadow_experiment_outcomes/experiment_outcomes.csv",
    output_dir: str = "reports/strategy_relaxation_suggestions",
) -> dict[str, Any]:
    default_exp_comp = "reports/shadow_experiment_comparison/experiment_comparison.csv"
    default_exp_promo = "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv"
    default_exp_outcomes = "reports/shadow_experiment_outcomes/experiment_outcomes.csv"
    report_root = Path(observation_samples_csv).resolve().parent.parent
    if str(shadow_experiment_comparison_csv) == default_exp_comp:
        shadow_experiment_comparison_csv = str(report_root / "shadow_experiment_comparison" / "experiment_comparison.csv")
    if str(shadow_experiment_promotion_csv) == default_exp_promo:
        shadow_experiment_promotion_csv = str(
            report_root / "shadow_experiment_promotion" / "experiment_promotion_decisions.csv"
        )
    if str(shadow_experiment_outcomes_csv) == default_exp_outcomes:
        shadow_experiment_outcomes_csv = str(report_root / "shadow_experiment_outcomes" / "experiment_outcomes.csv")

    gap_rows = read_csv_rows(Path(near_miss_strict_gap_csv))
    observation_rows = read_csv_rows(Path(observation_samples_csv))
    near_rows = read_csv_rows(Path(near_miss_scores_csv))
    quality_dashboard = _read_json(Path(shadow_quality_dashboard_json))
    exp_comp_rows = read_csv_rows(Path(shadow_experiment_comparison_csv))
    exp_promo_rows = read_csv_rows(Path(shadow_experiment_promotion_csv))
    exp_outcome_rows = read_csv_rows(Path(shadow_experiment_outcomes_csv))

    obs_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for row in observation_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            obs_by_strategy.setdefault(key, []).append(row)

    near_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for row in near_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            near_by_strategy.setdefault(key, []).append(row)

    gap_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for row in gap_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            gap_by_strategy.setdefault(key, []).append(row)

    exp_comp_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for row in exp_comp_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            exp_comp_by_strategy.setdefault(key, []).append(row)

    exp_promo_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for row in exp_promo_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            exp_promo_by_strategy.setdefault(key, []).append(row)

    exp_outcome_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for row in exp_outcome_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            exp_outcome_by_strategy.setdefault(key, []).append(row)

    all_keys = sorted(
        set(obs_by_strategy.keys())
        | set(gap_by_strategy.keys())
        | set(near_by_strategy.keys())
        | set(exp_comp_by_strategy.keys())
        | set(exp_promo_by_strategy.keys())
        | set(exp_outcome_by_strategy.keys())
    )
    out_rows: list[dict[str, Any]] = []
    for strategy_key in all_keys:
        obs_rows = list(obs_by_strategy.get(strategy_key, []))
        gaps = list(gap_by_strategy.get(strategy_key, []))
        near_items = list(near_by_strategy.get(strategy_key, []))
        exp_comps = list(exp_comp_by_strategy.get(strategy_key, []))
        exp_promos = list(exp_promo_by_strategy.get(strategy_key, []))
        exp_outcomes = list(exp_outcome_by_strategy.get(strategy_key, []))
        sample_count = len(obs_rows)
        first = obs_rows[0] if obs_rows else (gaps[0] if gaps else (near_items[0] if near_items else {}))
        symbol = str(first.get("symbol", "")).strip().upper()
        side = str(first.get("side", "")).strip().upper()
        timeframe = str(first.get("timeframe", "5m")).strip() or "5m"
        safe_gap_rows = [row for row in gaps if str(row.get("safe_to_experiment", "")).strip().lower() in {"true", "1"}]
        suggestion_type = "NO_CHANGE"
        if safe_gap_rows:
            suggestion_type = _map_gap_to_suggestion(safe_gap_rows[0].get("suggested_relaxation_type", ""))
        elif gaps:
            suggestion_type = _map_gap_to_suggestion(gaps[0].get("suggested_relaxation_type", ""))
        if not gaps:
            suggestion_type = "KEEP_STRICT"
        current_threshold, suggested_threshold = _threshold_pair(suggestion_type)
        observation_ids = sorted(
            set(
                str(row.get("observation_sample_id", "")).strip()
                for row in (safe_gap_rows if safe_gap_rows else gaps)
                if str(row.get("observation_sample_id", "")).strip()
            )
        )

        suggestion_verdict = "INSUFFICIENT_DATA"
        updated_suggestion_verdict = "INSUFFICIENT_DATA"
        confidence_level = "LOW"
        risk_level = "LOW_CONFIDENCE"
        reasons: list[str] = []
        if sample_count < 3:
            suggestion_verdict = "INSUFFICIENT_DATA"
            reasons.append("need_more_observation_samples")
        else:
            has_ignore = any(str(row.get("near_miss_verdict", "")).strip().upper() == "IGNORE" for row in near_items)
            if has_ignore:
                suggestion_verdict = "REJECT"
                confidence_level = "MEDIUM"
                risk_level = "ELEVATED"
                reasons.append("near_miss_quality_poor")
            elif safe_gap_rows:
                suggestion_verdict = "EXPERIMENT_ALLOWED"
                confidence_level = "MEDIUM"
                risk_level = "CONTROLLED"
                reasons.append("safe_gap_samples_available")
            else:
                suggestion_verdict = "WATCH_ONLY"
                confidence_level = "LOW"
                risk_level = "LOW_CONFIDENCE"
                reasons.append("gap_not_safe_yet")

        if suggestion_type in {"KEEP_STRICT", "NO_CHANGE"} and suggestion_verdict == "EXPERIMENT_ALLOWED":
            suggestion_verdict = "WATCH_ONLY"
            reasons.append("no_clear_relaxation_dimension")

        linked_experiment_ids = {
            str(row.get("experiment_id", "")).strip()
            for row in (exp_comps + exp_promos + exp_outcomes)
            if str(row.get("experiment_id", "")).strip()
        }
        linked_experiment_count = len(linked_experiment_ids)
        linked_experiment_candidate_count = 0
        for row in exp_comps:
            text = str(row.get("sample_count", "")).strip()
            if not text:
                continue
            try:
                value = int(float(text))
            except (TypeError, ValueError):
                continue
            linked_experiment_candidate_count += max(0, value)
        if linked_experiment_candidate_count <= 0:
            linked_experiment_candidate_count = len(
                {
                    str(row.get("experiment_candidate_id", "")).strip()
                    for row in exp_outcomes
                    if str(row.get("experiment_candidate_id", "")).strip()
                }
            )
        linked_experiment_evaluated_count = sum(
            1
            for row in exp_outcomes
            if str(row.get("evaluation_status", "")).strip().upper() not in {"", "PARTIAL"}
            and str(row.get("outcome", "")).strip().upper() not in {"UNKNOWN", "INSUFFICIENT_DATA", "MISSING_KLINES"}
        )
        best_experiment_type = "UNKNOWN"
        best_experiment_realized_r = float("nan")
        for row in exp_comps:
            value = row.get("avg_realized_r", "")
            try:
                current_r = float(value)
            except (TypeError, ValueError):
                continue
            if best_experiment_type == "UNKNOWN" or current_r > best_experiment_realized_r:
                best_experiment_realized_r = current_r
                best_experiment_type = str(row.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN"

        experiment_support_status = "NO_EXPERIMENTS"
        if linked_experiment_count <= 0:
            experiment_support_status = "NO_EXPERIMENTS"
        elif linked_experiment_candidate_count < 5 or linked_experiment_evaluated_count < 5:
            experiment_support_status = "INSUFFICIENT_EXPERIMENT_DATA"
        else:
            has_reject = any(
                str(row.get("promotion_decision", "")).strip().upper() == "REJECT_EXPERIMENT" for row in exp_promos
            )
            has_promote = any(
                str(row.get("promotion_decision", "")).strip().upper()
                in {"PROMOTE_TO_SHADOW_OBSERVATION", "PROMOTE_TO_STRICT_CANDIDATE_TEST"}
                for row in exp_promos
            )
            if has_reject or (best_experiment_type != "UNKNOWN" and best_experiment_realized_r < -0.1):
                experiment_support_status = "EXPERIMENT_REJECTS_RELAXATION"
            elif has_promote and best_experiment_type != "UNKNOWN" and best_experiment_realized_r > 0:
                experiment_support_status = "EXPERIMENT_SUPPORTS_RELAXATION"
            else:
                experiment_support_status = "MIXED"

        updated_suggestion_verdict = suggestion_verdict
        if experiment_support_status in {"NO_EXPERIMENTS", "INSUFFICIENT_EXPERIMENT_DATA"}:
            updated_suggestion_verdict = "INSUFFICIENT_DATA"
            reasons.append("need_more_experiment_samples")
        elif experiment_support_status == "EXPERIMENT_REJECTS_RELAXATION":
            updated_suggestion_verdict = "REJECT"
            reasons.append("experiment_rejects_relaxation")
        elif experiment_support_status == "EXPERIMENT_SUPPORTS_RELAXATION":
            if suggestion_verdict in {"WATCH_ONLY", "EXPERIMENT_ALLOWED"} and sample_count >= 10:
                updated_suggestion_verdict = "EXPERIMENT_ALLOWED"
            else:
                updated_suggestion_verdict = "WATCH_ONLY"
                reasons.append("observation_sample_still_small")
        elif experiment_support_status == "MIXED":
            updated_suggestion_verdict = "WATCH_ONLY"
            reasons.append("experiment_signal_mixed")

        expected_effect = "improve_signal_coverage"
        if suggestion_type in {"KEEP_STRICT", "NO_CHANGE"}:
            expected_effect = "preserve_filter_quality"
        if updated_suggestion_verdict in {"INSUFFICIENT_DATA", "WATCH_ONLY"}:
            expected_effect = "collect_more_observation_samples"

        out_rows.append(
            {
                "suggestion_id": f"sugg_{strategy_key}",
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "suggestion_type": suggestion_type,
                "current_threshold": current_threshold,
                "suggested_threshold": suggested_threshold,
                "expected_effect": expected_effect,
                "risk_level": risk_level,
                "confidence_level": confidence_level,
                "supporting_sample_count": sample_count,
                "supporting_observation_ids": ";".join(observation_ids),
                "linked_experiment_count": linked_experiment_count,
                "linked_experiment_candidate_count": linked_experiment_candidate_count,
                "linked_experiment_evaluated_count": linked_experiment_evaluated_count,
                "best_experiment_type": best_experiment_type,
                "best_experiment_realized_r": best_experiment_realized_r,
                "experiment_support_status": experiment_support_status,
                "updated_suggestion_verdict": updated_suggestion_verdict,
                "suggestion_verdict": suggestion_verdict,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "strategy_relaxation_suggestions.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if out_rows else "PARTIAL",
        "suggestion_count": len(out_rows),
        "experiment_allowed_count": sum(
            1 for row in out_rows if str(row.get("suggestion_verdict", "")).strip().upper() == "EXPERIMENT_ALLOWED"
        ),
        "watch_only_count": sum(1 for row in out_rows if str(row.get("suggestion_verdict", "")).strip().upper() == "WATCH_ONLY"),
        "updated_watch_only_count": sum(
            1 for row in out_rows if str(row.get("updated_suggestion_verdict", "")).strip().upper() == "WATCH_ONLY"
        ),
        "insufficient_data_count": sum(
            1 for row in out_rows if str(row.get("suggestion_verdict", "")).strip().upper() == "INSUFFICIENT_DATA"
        ),
        "updated_insufficient_data_count": sum(
            1 for row in out_rows if str(row.get("updated_suggestion_verdict", "")).strip().upper() == "INSUFFICIENT_DATA"
        ),
        "shadow_quality_final_verdict": str(quality_dashboard.get("final_verdict", "")).strip().upper() or "UNKNOWN",
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Strategy Relaxation Suggestions",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- suggestion_count: {summary['suggestion_count']}",
        f"- experiment_allowed_count: {summary['experiment_allowed_count']}",
        f"- watch_only_count: {summary['watch_only_count']}",
        f"- insufficient_data_count: {summary['insufficient_data_count']}",
        f"- updated_watch_only_count: {summary['updated_watch_only_count']}",
        f"- updated_insufficient_data_count: {summary['updated_insufficient_data_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate conservative strategy relaxation suggestions from near-miss gap analysis")
    parser.add_argument("--near-miss-strict-gap-csv", default="reports/near_miss_strict_gap/near_miss_strict_gap.csv")
    parser.add_argument("--observation-samples-csv", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--near-miss-scores-csv", default="reports/shadow_near_miss/near_miss_scores.csv")
    parser.add_argument("--shadow-quality-dashboard-json", default="reports/shadow_sample_quality/shadow_sample_quality_dashboard.json")
    parser.add_argument("--shadow-experiment-comparison-csv", default="reports/shadow_experiment_comparison/experiment_comparison.csv")
    parser.add_argument("--shadow-experiment-promotion-csv", default="reports/shadow_experiment_promotion/experiment_promotion_decisions.csv")
    parser.add_argument("--shadow-experiment-outcomes-csv", default="reports/shadow_experiment_outcomes/experiment_outcomes.csv")
    parser.add_argument("--output-dir", default="reports/strategy_relaxation_suggestions")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_strategy_relaxation_suggestions(
        near_miss_strict_gap_csv=str(args.near_miss_strict_gap_csv or "reports/near_miss_strict_gap/near_miss_strict_gap.csv"),
        observation_samples_csv=str(args.observation_samples_csv or "reports/observation_sample_store/observation_samples.csv"),
        near_miss_scores_csv=str(args.near_miss_scores_csv or "reports/shadow_near_miss/near_miss_scores.csv"),
        shadow_quality_dashboard_json=str(
            args.shadow_quality_dashboard_json or "reports/shadow_sample_quality/shadow_sample_quality_dashboard.json"
        ),
        shadow_experiment_comparison_csv=str(
            args.shadow_experiment_comparison_csv or "reports/shadow_experiment_comparison/experiment_comparison.csv"
        ),
        shadow_experiment_promotion_csv=str(
            args.shadow_experiment_promotion_csv or "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv"
        ),
        shadow_experiment_outcomes_csv=str(
            args.shadow_experiment_outcomes_csv or "reports/shadow_experiment_outcomes/experiment_outcomes.csv"
        ),
        output_dir=str(args.output_dir or "reports/strategy_relaxation_suggestions"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"suggestion_count={result.get('suggestion_count', 0)}")


if __name__ == "__main__":
    main()
