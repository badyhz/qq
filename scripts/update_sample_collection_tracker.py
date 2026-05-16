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
    to_float_nan,
)


FIELDS = [
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "current_real_trade_samples",
    "current_shadow_samples",
    "total_effective_samples",
    "shadow_sample_weight",
    "strict_shadow_samples",
    "observation_shadow_samples",
    "observation_shadow_weight",
    "weighted_observation_samples",
    "weighted_sample_count",
    "weighted_confidence_level",
    "minimum_required_samples",
    "samples_needed_for_low",
    "samples_needed_for_medium",
    "samples_needed_for_high",
    "samples_needed_weighted_for_low",
    "samples_needed_weighted_for_medium",
    "samples_needed_weighted_for_high",
    "samples_needed_after_observation_weight",
    "today_new_shadow_samples",
    "collection_priority",
    "collection_status",
    "next_action",
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except OSError:
        return []
    return rows


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def _to_date_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date().isoformat()
    except ValueError:
        return ""


def update_sample_collection_tracker(
    *,
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    collect_plan_csv: str = "reports/collect_more_samples_plan/collect_more_samples_plan.csv",
    shadow_candidates_jsonl: str = "logs/shadow_candidates.jsonl",
    shadow_candidates_csv: str = "reports/shadow_candidate_collection/shadow_candidates.csv",
    output_dir: str = "reports/sample_collection_tracker",
    shadow_sample_weight: float = 0.3,
    observation_shadow_weight: float = 0.1,
) -> dict[str, Any]:
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))
    collect_rows = read_csv_rows(Path(collect_plan_csv))
    shadow_jsonl_rows = _load_jsonl(Path(shadow_candidates_jsonl))
    shadow_csv_rows = read_csv_rows(Path(shadow_candidates_csv))

    today = datetime.now(timezone.utc).date().isoformat()
    shadow_by_strategy: dict[str, set[str]] = {}
    strict_shadow_by_strategy: dict[str, set[str]] = {}
    observation_shadow_by_strategy: dict[str, set[str]] = {}
    shadow_today_by_strategy: dict[str, int] = {}
    for row in shadow_jsonl_rows:
        strategy_key = str(row.get("strategy_key", "")).strip()
        candidate_id = str(row.get("candidate_id", "")).strip()
        if not strategy_key:
            continue
        shadow_by_strategy.setdefault(strategy_key, set())
        strict_shadow_by_strategy.setdefault(strategy_key, set())
        observation_shadow_by_strategy.setdefault(strategy_key, set())
        if candidate_id:
            shadow_by_strategy[strategy_key].add(candidate_id)
            is_observation = str(row.get("candidate_status", "")).strip().upper() == "SHADOW_OBSERVATION_ONLY"
            if is_observation:
                observation_shadow_by_strategy[strategy_key].add(candidate_id)
            else:
                strict_shadow_by_strategy[strategy_key].add(candidate_id)
        date_text = _to_date_text(str(row.get("created_at", "")))
        if date_text == today:
            shadow_today_by_strategy[strategy_key] = int(shadow_today_by_strategy.get(strategy_key, 0)) + 1
    for row in shadow_csv_rows:
        strategy_key = str(row.get("strategy_key", "")).strip()
        candidate_id = str(row.get("candidate_id", "")).strip()
        if strategy_key and candidate_id:
            shadow_by_strategy.setdefault(strategy_key, set()).add(candidate_id)
            strict_shadow_by_strategy.setdefault(strategy_key, set())
            observation_shadow_by_strategy.setdefault(strategy_key, set())
            is_observation = str(row.get("candidate_status", "")).strip().upper() == "SHADOW_OBSERVATION_ONLY"
            if is_observation:
                observation_shadow_by_strategy[strategy_key].add(candidate_id)
            else:
                strict_shadow_by_strategy[strategy_key].add(candidate_id)

    collect_index = {str(row.get("strategy_key", "")).strip(): row for row in collect_rows if str(row.get("strategy_key", "")).strip()}

    out_rows: list[dict[str, Any]] = []
    for row in strategy_rows:
        strategy_key = str(row.get("strategy_key", "")).strip()
        if not strategy_key:
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        side = _normalize_side(row.get("side", "LONG"))
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        real_samples = int(
            to_float_nan(row.get("real_sample_count"))
            if math.isfinite(to_float_nan(row.get("real_sample_count")))
            else (to_float_nan(row.get("sample_count")) if math.isfinite(to_float_nan(row.get("sample_count"))) else 0)
        )
        strict_shadow_from_score = to_float_nan(row.get("strict_shadow_sample_count"))
        observation_shadow_from_score = to_float_nan(row.get("observation_shadow_sample_count"))
        strict_shadow_samples = int(strict_shadow_from_score) if math.isfinite(strict_shadow_from_score) else len(strict_shadow_by_strategy.get(strategy_key, set()))
        observation_shadow_samples = (
            int(observation_shadow_from_score) if math.isfinite(observation_shadow_from_score) else len(observation_shadow_by_strategy.get(strategy_key, set()))
        )
        shadow_samples = strict_shadow_samples + observation_shadow_samples
        total_samples = real_samples + shadow_samples
        weighted_observation_samples = float(observation_shadow_samples) * float(observation_shadow_weight)
        weighted_samples = compute_weighted_sample_count_with_observation(
            real_sample_count=real_samples,
            strict_shadow_sample_count=strict_shadow_samples,
            observation_shadow_sample_count=observation_shadow_samples,
            strict_shadow_sample_weight=shadow_sample_weight,
            observation_shadow_sample_weight=observation_shadow_weight,
        )
        weighted_conf = evaluate_weighted_sample_confidence(
            weighted_sample_count=weighted_samples,
            minimum_required_samples=20,
        )
        weighted_conf_level = str(weighted_conf.get("sample_confidence_level", "TOO_SMALL")).strip().upper() or "TOO_SMALL"
        min_required = int(to_float_nan(row.get("minimum_required_samples")) if math.isfinite(to_float_nan(row.get("minimum_required_samples"))) else 20)

        need_low = max(0, 5 - total_samples)
        need_medium = max(0, 20 - total_samples)
        need_high = max(0, 50 - total_samples)
        need_weighted_low = max(0.0, 5.0 - weighted_samples)
        need_weighted_medium = max(0.0, 20.0 - weighted_samples)
        need_weighted_high = max(0.0, 50.0 - weighted_samples)
        samples_needed_after_observation_weight = need_weighted_medium

        collect_plan = collect_index.get(strategy_key, {})
        priority = str(collect_plan.get("collection_priority", "P2")).strip().upper() or "P2"
        if weighted_samples >= 50.0:
            status = "HIGH_CONFIDENCE"
            next_action = "ready_for_high_confidence_review"
        elif weighted_samples >= 20.0:
            status = "MEDIUM_READY"
            next_action = "review_for_promotion"
        elif weighted_samples <= 0:
            status = "NOT_STARTED"
            next_action = "start_shadow_collection"
        elif shadow_samples > 0:
            status = "COLLECTING"
            next_action = "collect_more_shadow_samples"
        else:
            status = "LOW_CONFIDENCE"
            next_action = "collect_more_shadow_samples"
        if str(collect_plan.get("collection_mode", "")).strip().upper() == "BLOCKED":
            status = "PAUSED"
            next_action = "manual_review"

        out_rows.append(
            {
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "current_real_trade_samples": real_samples,
                "current_shadow_samples": shadow_samples,
                "total_effective_samples": total_samples,
                "shadow_sample_weight": round(float(shadow_sample_weight), 8),
                "strict_shadow_samples": strict_shadow_samples,
                "observation_shadow_samples": observation_shadow_samples,
                "observation_shadow_weight": round(float(observation_shadow_weight), 8),
                "weighted_observation_samples": round(weighted_observation_samples, 8),
                "weighted_sample_count": round(weighted_samples, 8),
                "weighted_confidence_level": weighted_conf_level,
                "minimum_required_samples": min_required,
                "samples_needed_for_low": need_low,
                "samples_needed_for_medium": need_medium,
                "samples_needed_for_high": need_high,
                "samples_needed_weighted_for_low": round(need_weighted_low, 8),
                "samples_needed_weighted_for_medium": round(need_weighted_medium, 8),
                "samples_needed_weighted_for_high": round(need_weighted_high, 8),
                "samples_needed_after_observation_weight": round(samples_needed_after_observation_weight, 8),
                "today_new_shadow_samples": int(shadow_today_by_strategy.get(strategy_key, 0)),
                "collection_priority": priority,
                "collection_status": status,
                "next_action": next_action,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "sample_collection_tracker.csv"
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
        "strategy_count": len(out_rows),
        "collecting_count": sum(1 for row in out_rows if str(row.get("collection_status", "")).upper() == "COLLECTING"),
        "low_confidence_count": sum(1 for row in out_rows if str(row.get("collection_status", "")).upper() == "LOW_CONFIDENCE"),
        "medium_ready_count": sum(1 for row in out_rows if str(row.get("collection_status", "")).upper() == "MEDIUM_READY"),
        "high_confidence_count": sum(1 for row in out_rows if str(row.get("collection_status", "")).upper() == "HIGH_CONFIDENCE"),
        "today_new_shadow_samples_total": sum(int(row.get("today_new_shadow_samples", 0)) for row in out_rows),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Sample Collection Tracker",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- strategy_count: {summary['strategy_count']}",
        f"- collecting_count: {summary['collecting_count']}",
        f"- low_confidence_count: {summary['low_confidence_count']}",
        f"- medium_ready_count: {summary['medium_ready_count']}",
        f"- high_confidence_count: {summary['high_confidence_count']}",
        f"- today_new_shadow_samples_total: {summary['today_new_shadow_samples_total']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update sample collection tracker from strategy and shadow artifacts")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--collect-plan-csv", default="reports/collect_more_samples_plan/collect_more_samples_plan.csv")
    parser.add_argument("--shadow-candidates-jsonl", default="logs/shadow_candidates.jsonl")
    parser.add_argument("--shadow-candidates-csv", default="reports/shadow_candidate_collection/shadow_candidates.csv")
    parser.add_argument("--shadow-sample-weight", type=float, default=0.3)
    parser.add_argument("--observation-shadow-weight", type=float, default=0.1)
    parser.add_argument("--output-dir", default="reports/sample_collection_tracker")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = update_sample_collection_tracker(
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        collect_plan_csv=str(args.collect_plan_csv or "reports/collect_more_samples_plan/collect_more_samples_plan.csv"),
        shadow_candidates_jsonl=str(args.shadow_candidates_jsonl or "logs/shadow_candidates.jsonl"),
        shadow_candidates_csv=str(args.shadow_candidates_csv or "reports/shadow_candidate_collection/shadow_candidates.csv"),
        output_dir=str(args.output_dir or "reports/sample_collection_tracker"),
        shadow_sample_weight=float(args.shadow_sample_weight if args.shadow_sample_weight is not None else 0.3),
        observation_shadow_weight=float(args.observation_shadow_weight if args.observation_shadow_weight is not None else 0.1),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"strategy_count={result.get('strategy_count', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
