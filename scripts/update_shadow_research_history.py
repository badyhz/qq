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
    "current_phase",
    "total_experiments",
    "next_run_candidate_count",
    "sample_gap_total",
    "needs_more_data_count",
    "allow_increase_shadow_frequency",
    "allow_testnet_dry_run",
    "allow_testnet_submit",
    "allow_real_submit",
    "recommended_next_action",
    "final_verdict",
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


def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if parsed != parsed:
        return int(default)
    return int(parsed)


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def update_shadow_research_history(
    *,
    daily_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    shadow_research_recompute_json: str = "reports/shadow_research_recompute/recompute_report.json",
    frequency_review_json: str = "reports/shadow_experiment_frequency_review/frequency_review.json",
    testnet_dry_run_readiness_json: str = "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json",
    output_dir: str = "reports/shadow_research_history",
    rebuild: bool = False,
) -> dict[str, Any]:
    daily = _read_json(Path(daily_research_control_json))
    recompute = _read_json(Path(shadow_research_recompute_json))
    frequency = _read_json(Path(frequency_review_json))
    readiness = _read_json(Path(testnet_dry_run_readiness_json))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "shadow_research_history.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"

    existing_rows = [] if rebuild else read_csv_rows(csv_path)
    now = datetime.now(timezone.utc)
    run_date = now.date().isoformat()
    current_phase = str(daily.get("current_phase", "SHADOW_EXPERIMENT_COLLECTION")).strip().upper() or "SHADOW_EXPERIMENT_COLLECTION"
    row_key = f"{run_date}|{current_phase}"
    dedupe_keys = {f"{str(r.get('run_date','')).strip()}|{str(r.get('current_phase','')).strip().upper()}" for r in existing_rows}

    appended = False
    if row_key not in dedupe_keys:
        existing_rows.append(
            {
                "history_id": f"srh_{run_date}_{current_phase}".lower(),
                "run_date": run_date,
                "current_phase": current_phase,
                "total_experiments": _to_int(daily.get("total_experiments"), 0),
                "next_run_candidate_count": _to_int(daily.get("next_run_candidate_count"), _to_int(recompute.get("next_run_candidate_count"), 0)),
                "sample_gap_total": _to_int(daily.get("sample_gap_total"), 0),
                "needs_more_data_count": _to_int(daily.get("needs_more_data_count"), 0),
                "allow_increase_shadow_frequency": bool(frequency.get("allow_increase_shadow_frequency", False)),
                "allow_testnet_dry_run": bool(readiness.get("allow_testnet_dry_run", False)),
                "allow_testnet_submit": False,
                "allow_real_submit": False,
                "recommended_next_action": str(daily.get("recommended_next_action", "RUN_SHADOW_ONLY_LOOP_ONCE")).strip().upper() or "RUN_SHADOW_ONLY_LOOP_ONCE",
                "final_verdict": str(daily.get("final_verdict", "PARTIAL")).strip().upper() or "PARTIAL",
                "created_at": now.isoformat(),
            }
        )
        appended = True

    # normalize and enforce safety booleans
    normalized_rows: list[dict[str, Any]] = []
    for row in existing_rows:
        item = dict(row)
        item["allow_testnet_submit"] = False
        item["allow_real_submit"] = False
        item["allow_testnet_dry_run"] = bool(_to_bool(item.get("allow_testnet_dry_run")))
        item["allow_increase_shadow_frequency"] = bool(_to_bool(item.get("allow_increase_shadow_frequency")))
        normalized_rows.append(item)

    normalized_rows.sort(key=lambda item: (str(item.get("run_date", "")), str(item.get("current_phase", ""))))
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in normalized_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": now.isoformat(),
        "final_verdict": "PASS" if normalized_rows else "PARTIAL",
        "rebuild": bool(rebuild),
        "appended": bool(appended),
        "history_row_count": len(normalized_rows),
        "current_phase": current_phase,
        "allow_testnet_submit": False,
        "allow_real_submit": False,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Research History",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- rebuild: {str(summary['rebuild']).lower()}",
        f"- appended: {str(summary['appended']).lower()}",
        f"- history_row_count: {summary['history_row_count']}",
        f"- current_phase: {summary['current_phase']}",
        "- allow_testnet_submit: false",
        "- allow_real_submit: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append or rebuild shadow research history")
    parser.add_argument("--daily-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--shadow-research-recompute-json", default="reports/shadow_research_recompute/recompute_report.json")
    parser.add_argument("--frequency-review-json", default="reports/shadow_experiment_frequency_review/frequency_review.json")
    parser.add_argument("--testnet-dry-run-readiness-json", default="reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json")
    parser.add_argument("--output-dir", default="reports/shadow_research_history")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = update_shadow_research_history(
        daily_research_control_json=str(
            args.daily_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        shadow_research_recompute_json=str(
            args.shadow_research_recompute_json or "reports/shadow_research_recompute/recompute_report.json"
        ),
        frequency_review_json=str(args.frequency_review_json or "reports/shadow_experiment_frequency_review/frequency_review.json"),
        testnet_dry_run_readiness_json=str(
            args.testnet_dry_run_readiness_json or "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json"
        ),
        output_dir=str(args.output_dir or "reports/shadow_research_history"),
        rebuild=bool(args.rebuild),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"history_row_count={result.get('history_row_count', 0)}")


if __name__ == "__main__":
    main()
