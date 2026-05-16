from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "history_id",
    "run_date",
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "experiment_candidate_count",
    "evaluated_count",
    "sample_count",
    "avg_realized_r",
    "comparison_verdict",
    "promotion_decision",
    "next_experiment_status",
    "risk_level",
    "required_next_samples",
    "final_eod_verdict",
    "recommended_next_action",
    "allowed_mode",
    "testnet_submit_allowed",
    "real_submit_allowed",
    "created_at",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _run_date_from_eod(eod: dict[str, Any]) -> str:
    text = str(eod.get("generated_at_utc", "")).strip()
    if not text:
        return datetime.now(timezone.utc).date().isoformat()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return datetime.now(timezone.utc).date().isoformat()


def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if not (parsed == parsed):
        return int(default)
    return int(parsed)


def update_shadow_experiment_history(
    *,
    experiment_eod_report_json: str = "reports/shadow_experiment_eod/experiment_eod_report.json",
    experiment_promotion_decisions_csv: str = "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    experiment_comparison_csv: str = "reports/shadow_experiment_comparison/experiment_comparison.csv",
    experiment_runs_summary_json: str = "reports/shadow_observation_experiment_runs/summary.json",
    experiment_outcomes_summary_json: str = "reports/shadow_experiment_outcomes/summary.json",
    output_dir: str = "reports/shadow_experiment_history",
    rebuild: bool = False,
) -> dict[str, Any]:
    eod = _read_json(Path(experiment_eod_report_json))
    promotion_rows = read_csv_rows(Path(experiment_promotion_decisions_csv))
    comparison_rows = read_csv_rows(Path(experiment_comparison_csv))
    runs_summary = _read_json(Path(experiment_runs_summary_json))
    outcomes_summary = _read_json(Path(experiment_outcomes_summary_json))

    comparison_index = {
        str(row.get("experiment_id", "")).strip(): row
        for row in comparison_rows
        if str(row.get("experiment_id", "")).strip()
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiment_history.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"

    existing_rows: list[dict[str, Any]] = []
    if (not rebuild) and csv_path.exists():
        existing_rows = read_csv_rows(csv_path)

    row_map: dict[str, dict[str, Any]] = {
        str(row.get("history_id", "")).strip(): row
        for row in existing_rows
        if str(row.get("history_id", "")).strip()
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    run_date = _run_date_from_eod(eod)
    final_eod_verdict = str(eod.get("final_verdict", "PARTIAL")).strip().upper() or "PARTIAL"
    recommended_next_action = str(eod.get("recommended_next_action", "CONTINUE_SHADOW_EXPERIMENT_COLLECTION")).strip()
    allowed_mode = str(eod.get("allowed_mode", "SHADOW_ONLY")).strip().upper() or "SHADOW_ONLY"
    testnet_submit_allowed = bool(eod.get("testnet_submit_allowed", False))
    real_submit_allowed = bool(eod.get("real_submit_allowed", False))

    default_candidate_count = _to_int(runs_summary.get("experiment_candidate_count"), 0)
    if default_candidate_count < 0:
        default_candidate_count = 0
    default_evaluated_count = _to_int(outcomes_summary.get("evaluated_count"), 0)
    if default_evaluated_count < 0:
        default_evaluated_count = 0

    inserted = 0
    for promo in promotion_rows:
        experiment_id = str(promo.get("experiment_id", "")).strip()
        if not experiment_id:
            continue
        comp = comparison_index.get(experiment_id, {})
        sample_count = _to_int(comp.get("sample_count"), 0)
        if sample_count < 0:
            sample_count = 0
        evaluated_count = _to_int(comp.get("primary_horizon_evaluated_count"), 0)
        if evaluated_count < 0:
            evaluated_count = 0
        experiment_candidate_count = sample_count if sample_count > 0 else default_candidate_count
        if experiment_candidate_count <= 0:
            experiment_candidate_count = _to_int(promo.get("sample_count"), 0)
            if experiment_candidate_count < 0:
                experiment_candidate_count = 0
        if evaluated_count <= 0:
            evaluated_count = default_evaluated_count

        history_id = f"{run_date}_{experiment_id}"
        row_map[history_id] = {
            "history_id": history_id,
            "run_date": run_date,
            "experiment_id": experiment_id,
            "strategy_key": str(promo.get("strategy_key", "")).strip(),
            "symbol": str(promo.get("symbol", "")).strip().upper(),
            "side": str(promo.get("side", "")).strip().upper(),
            "timeframe": str(promo.get("timeframe", "5m")).strip() or "5m",
            "experiment_type": str(promo.get("experiment_type", "")).strip().upper(),
            "experiment_candidate_count": experiment_candidate_count,
            "evaluated_count": evaluated_count,
            "sample_count": sample_count,
            "avg_realized_r": to_float_nan(comp.get("avg_realized_r")),
            "comparison_verdict": str(comp.get("comparison_verdict", "INSUFFICIENT_DATA")).strip().upper(),
            "promotion_decision": str(promo.get("promotion_decision", "KEEP_COLLECTING")).strip().upper(),
            "next_experiment_status": str(promo.get("next_experiment_status", "WATCH_ONLY")).strip().upper(),
            "risk_level": str(promo.get("risk_level", "LOW_CONFIDENCE")).strip().upper(),
                "required_next_samples": _to_int(promo.get("required_next_samples"), 0),
            "final_eod_verdict": final_eod_verdict,
            "recommended_next_action": recommended_next_action,
            "allowed_mode": "SHADOW_ONLY" if allowed_mode != "SHADOW_ONLY" else allowed_mode,
            "testnet_submit_allowed": False if testnet_submit_allowed else False,
            "real_submit_allowed": False if real_submit_allowed else False,
            "created_at": now_iso,
        }
        inserted += 1

    rows = sorted(row_map.values(), key=lambda row: (str(row.get("run_date", "")), str(row.get("history_id", ""))))
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": now_iso,
        "final_verdict": "PASS" if rows else "PARTIAL",
        "history_row_count": len(rows),
        "inserted_or_updated_count": inserted,
        "run_date": run_date,
        "keep_collecting_count": sum(
            1 for row in rows if str(row.get("promotion_decision", "")).strip().upper() == "KEEP_COLLECTING"
        ),
        "promote_count": sum(
            1
            for row in rows
            if str(row.get("promotion_decision", "")).strip().upper()
            in {"PROMOTE_TO_SHADOW_OBSERVATION", "PROMOTE_TO_STRICT_CANDIDATE_TEST"}
        ),
        "reject_count": sum(
            1 for row in rows if str(row.get("promotion_decision", "")).strip().upper() == "REJECT_EXPERIMENT"
        ),
        "allowed_mode": "SHADOW_ONLY",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment History",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- history_row_count: {summary['history_row_count']}",
        f"- inserted_or_updated_count: {summary['inserted_or_updated_count']}",
        f"- keep_collecting_count: {summary['keep_collecting_count']}",
        f"- promote_count: {summary['promote_count']}",
        f"- reject_count: {summary['reject_count']}",
        "- allowed_mode: SHADOW_ONLY",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update or rebuild daily shadow experiment history")
    parser.add_argument("--experiment-eod-report-json", default="reports/shadow_experiment_eod/experiment_eod_report.json")
    parser.add_argument(
        "--experiment-promotion-decisions-csv",
        default="reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    )
    parser.add_argument("--experiment-comparison-csv", default="reports/shadow_experiment_comparison/experiment_comparison.csv")
    parser.add_argument("--experiment-runs-summary-json", default="reports/shadow_observation_experiment_runs/summary.json")
    parser.add_argument("--experiment-outcomes-summary-json", default="reports/shadow_experiment_outcomes/summary.json")
    parser.add_argument("--output-dir", default="reports/shadow_experiment_history")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = update_shadow_experiment_history(
        experiment_eod_report_json=str(args.experiment_eod_report_json or "reports/shadow_experiment_eod/experiment_eod_report.json"),
        experiment_promotion_decisions_csv=str(
            args.experiment_promotion_decisions_csv
            or "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv"
        ),
        experiment_comparison_csv=str(args.experiment_comparison_csv or "reports/shadow_experiment_comparison/experiment_comparison.csv"),
        experiment_runs_summary_json=str(
            args.experiment_runs_summary_json or "reports/shadow_observation_experiment_runs/summary.json"
        ),
        experiment_outcomes_summary_json=str(
            args.experiment_outcomes_summary_json or "reports/shadow_experiment_outcomes/summary.json"
        ),
        output_dir=str(args.output_dir or "reports/shadow_experiment_history"),
        rebuild=bool(args.rebuild),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"history_row_count={result.get('history_row_count', 0)}")


if __name__ == "__main__":
    main()
