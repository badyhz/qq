from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


HISTORY_DELTA_FIELDS = [
    "run_id",
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "planned_target_samples",
    "actual_new_candidates",
    "candidate_delta",
    "history_update_status",
    "reason",
]

TRACKER_DELTA_FIELDS = [
    "run_id",
    "experiment_id",
    "previous_sample_count",
    "new_sample_count",
    "planned_target_samples",
    "actual_new_candidates",
    "samples_needed_for_decision_before",
    "samples_needed_for_decision_after",
    "tracker_update_status",
    "next_action",
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
    if not (parsed == parsed):
        return int(default)
    return int(parsed)


def _load_registry(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(payload, list):
        return set()
    return {str(item).strip() for item in payload if str(item).strip()}


def _save_registry(path: Path, values: set[str]) -> None:
    path.write_text(json.dumps(sorted(values), ensure_ascii=False, indent=2), encoding="utf-8")


def apply_next_shadow_experiment_run_results(
    *,
    next_run_candidates_csv: str = "reports/next_shadow_experiment_run/next_run_candidates.csv",
    next_run_summary_json: str = "reports/next_shadow_experiment_run/summary.json",
    experiment_history_csv: str = "reports/shadow_experiment_history/experiment_history.csv",
    experiment_sample_tracker_csv: str = "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv",
    next_run_plan_csv: str = "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv",
    output_dir: str = "reports/next_shadow_experiment_run_applied",
    apply: bool = False,
    confirm_shadow_only: bool = False,
) -> dict[str, Any]:
    run_rows = read_csv_rows(Path(next_run_candidates_csv))
    run_summary = _read_json(Path(next_run_summary_json))
    history_rows = read_csv_rows(Path(experiment_history_csv))
    tracker_rows = read_csv_rows(Path(experiment_sample_tracker_csv))
    plan_rows = read_csv_rows(Path(next_run_plan_csv))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    history_delta_csv = out_dir / "applied_history_delta.csv"
    tracker_delta_csv = out_dir / "applied_tracker_delta.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    registry_json = out_dir / "processed_candidate_ids.json"
    audit_jsonl = out_dir / "apply_audit.jsonl"
    latest_audit_json = out_dir / "latest_apply_audit.json"

    processed_ids = _load_registry(registry_json)
    run_id = f"next_run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    plan_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in plan_rows
        if str(row.get("experiment_id", "")).strip()
    }
    tracker_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in tracker_rows
        if str(row.get("experiment_id", "")).strip()
    }
    latest_history_by_exp: dict[str, dict[str, Any]] = {}
    for row in sorted(history_rows, key=lambda item: (str(item.get("run_date", "")), str(item.get("created_at", "")))):
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            latest_history_by_exp[exp_id] = row

    new_candidates_by_exp: dict[str, list[dict[str, Any]]] = {}
    duplicate_skipped = 0
    for row in run_rows:
        cid = str(row.get("next_run_candidate_id", "")).strip()
        exp_id = str(row.get("experiment_id", "")).strip()
        if not cid or not exp_id:
            continue
        if cid in processed_ids:
            duplicate_skipped += 1
            continue
        new_candidates_by_exp.setdefault(exp_id, []).append(row)

    history_delta_rows: list[dict[str, Any]] = []
    tracker_delta_rows: list[dict[str, Any]] = []
    touched_experiments = sorted(set(plan_by_exp.keys()) | set(new_candidates_by_exp.keys()))
    for exp_id in touched_experiments:
        plan = plan_by_exp.get(exp_id, {})
        tracker = tracker_by_exp.get(exp_id, {})
        latest = latest_history_by_exp.get(exp_id, {})
        new_items = new_candidates_by_exp.get(exp_id, [])
        planned_target = _to_int(plan.get("target_samples_this_run"), 0)
        actual_new = len(new_items)
        prev_sample = _to_int(tracker.get("current_sample_count"), _to_int(latest.get("sample_count"), 0))
        prev_needed = _to_int(tracker.get("samples_needed_for_decision"), max(0, 20 - prev_sample))
        new_sample = prev_sample + actual_new
        new_needed = max(0, prev_needed - actual_new)

        history_status = "UPDATED" if actual_new > 0 else "NO_NEW_CANDIDATES"
        tracker_status = "UPDATED" if actual_new > 0 else "NO_CHANGE"
        reason = "new_candidates_applied" if actual_new > 0 else "no_new_candidates"
        next_action = "collect_more_shadow_experiment_samples"
        if new_needed <= 0:
            next_action = "decision_ready_recheck"

        history_delta_rows.append(
            {
                "run_id": run_id,
                "experiment_id": exp_id,
                "strategy_key": str(plan.get("strategy_key", latest.get("strategy_key", ""))).strip(),
                "symbol": str(plan.get("symbol", latest.get("symbol", ""))).strip().upper(),
                "side": str(plan.get("side", latest.get("side", ""))).strip().upper(),
                "timeframe": str(plan.get("timeframe", latest.get("timeframe", "5m"))).strip() or "5m",
                "experiment_type": str(plan.get("experiment_type", latest.get("experiment_type", "UNKNOWN"))).strip().upper()
                or "UNKNOWN",
                "planned_target_samples": planned_target,
                "actual_new_candidates": actual_new,
                "candidate_delta": actual_new - planned_target,
                "history_update_status": history_status,
                "reason": reason,
            }
        )
        tracker_delta_rows.append(
            {
                "run_id": run_id,
                "experiment_id": exp_id,
                "previous_sample_count": prev_sample,
                "new_sample_count": new_sample,
                "planned_target_samples": planned_target,
                "actual_new_candidates": actual_new,
                "samples_needed_for_decision_before": prev_needed,
                "samples_needed_for_decision_after": new_needed,
                "tracker_update_status": tracker_status,
                "next_action": next_action,
            }
        )

    with history_delta_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HISTORY_DELTA_FIELDS)
        writer.writeheader()
        for row in history_delta_rows:
            writer.writerow({field: row.get(field, "") for field in HISTORY_DELTA_FIELDS})
    with tracker_delta_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACKER_DELTA_FIELDS)
        writer.writeheader()
        for row in tracker_delta_rows:
            writer.writerow({field: row.get(field, "") for field in TRACKER_DELTA_FIELDS})

    applied_history_count = 0
    applied_tracker_count = 0
    apply_rejected = bool(apply and (not confirm_shadow_only))
    if bool(apply) and bool(confirm_shadow_only):
        now_iso = datetime.now(timezone.utc).isoformat()
        run_date = now_iso[:10]
        history_out = list(history_rows)
        for row in history_delta_rows:
            if int(row.get("actual_new_candidates", 0) or 0) <= 0:
                continue
            exp_id = str(row.get("experiment_id", "")).strip()
            latest = latest_history_by_exp.get(exp_id, {})
            base_sample = _to_int(latest.get("sample_count"), 0)
            new_sample = base_sample + _to_int(row.get("actual_new_candidates"), 0)
            history_out.append(
                {
                    "history_id": f"{run_date}_{exp_id}_{run_id}",
                    "run_date": run_date,
                    "experiment_id": exp_id,
                    "strategy_key": row.get("strategy_key", ""),
                    "symbol": row.get("symbol", ""),
                    "side": row.get("side", ""),
                    "timeframe": row.get("timeframe", "5m"),
                    "experiment_type": row.get("experiment_type", "UNKNOWN"),
                    "experiment_candidate_count": _to_int(row.get("actual_new_candidates"), 0),
                    "evaluated_count": 0,
                    "sample_count": new_sample,
                    "avg_realized_r": float("nan"),
                    "comparison_verdict": "INSUFFICIENT_DATA",
                    "promotion_decision": "KEEP_COLLECTING",
                    "next_experiment_status": "WATCH_ONLY",
                    "risk_level": "LOW_CONFIDENCE",
                    "required_next_samples": max(0, 20 - new_sample),
                    "final_eod_verdict": str(run_summary.get("final_verdict", "PARTIAL")).strip().upper() or "PARTIAL",
                    "recommended_next_action": "CONTINUE_SHADOW_EXPERIMENT_COLLECTION",
                    "allowed_mode": "SHADOW_ONLY",
                    "testnet_submit_allowed": False,
                    "real_submit_allowed": False,
                    "created_at": now_iso,
                }
            )
            applied_history_count += 1
        if history_out:
            fieldnames = sorted({key for item in history_out for key in item.keys()})
            with Path(experiment_history_csv).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(history_out)

        tracker_out = list(tracker_rows)
        tracker_index = {
            str(row.get("experiment_id", "")).strip(): idx
            for idx, row in enumerate(tracker_out)
            if str(row.get("experiment_id", "")).strip()
        }
        for row in tracker_delta_rows:
            if int(row.get("actual_new_candidates", 0) or 0) <= 0:
                continue
            exp_id = str(row.get("experiment_id", "")).strip()
            idx = tracker_index.get(exp_id, -1)
            if idx < 0:
                continue
            item = dict(tracker_out[idx])
            item["current_sample_count"] = _to_int(row.get("new_sample_count"), 0)
            item["samples_needed_for_decision"] = _to_int(row.get("samples_needed_for_decision_after"), 0)
            item["collection_status"] = "MINIMUM_NOT_MET" if _to_int(item.get("samples_needed_for_decision"), 0) > 0 else "DECISION_READY"
            item["next_action"] = row.get("next_action", "collect_more_shadow_experiment_samples")
            tracker_out[idx] = item
            applied_tracker_count += 1
        if tracker_out:
            fieldnames = sorted({key for item in tracker_out for key in item.keys()})
            with Path(experiment_sample_tracker_csv).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(tracker_out)

        for row in run_rows:
            cid = str(row.get("next_run_candidate_id", "")).strip()
            if cid:
                processed_ids.add(cid)
        _save_registry(registry_json, processed_ids)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if plan_rows else "PARTIAL",
        "run_id": run_id,
        "apply": bool(apply),
        "confirm_shadow_only": bool(confirm_shadow_only),
        "planned_experiment_count": len(plan_rows),
        "next_run_candidate_count": len(run_rows),
        "new_candidate_count_after_dedupe": sum(len(value) for value in new_candidates_by_exp.values()),
        "duplicate_candidate_skipped_count": duplicate_skipped,
        "applied_history_count": applied_history_count,
        "applied_tracker_count": applied_tracker_count,
        "allowed_mode": "SHADOW_ONLY",
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "history_delta_csv": str(history_delta_csv),
        "tracker_delta_csv": str(tracker_delta_csv),
        "audit_jsonl": str(audit_jsonl),
        "latest_apply_audit_json": str(latest_audit_json),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    if apply_rejected:
        summary["final_verdict"] = "FAIL"
        summary["error"] = "apply_requires_confirm_shadow_only"
    if sum(len(value) for value in new_candidates_by_exp.values()) == 0:
        summary["status_reason"] = "no_new_candidates"
        if len(plan_rows) > 0 and (not apply_rejected):
            summary["final_verdict"] = "PARTIAL"

    audit_payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "apply": bool(apply),
        "confirm_shadow_only": bool(confirm_shadow_only),
        "new_candidate_count_after_dedupe": summary.get("new_candidate_count_after_dedupe", 0),
        "applied_history_count": summary.get("applied_history_count", 0),
        "applied_tracker_count": summary.get("applied_tracker_count", 0),
        "duplicate_skipped_count": summary.get("duplicate_candidate_skipped_count", 0),
        "allowed_mode": "SHADOW_ONLY",
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }
    if apply_rejected:
        audit_payload["error"] = "apply_requires_confirm_shadow_only"

    existing_lines: list[str] = []
    if audit_jsonl.exists():
        try:
            existing_lines = audit_jsonl.read_text(encoding="utf-8").splitlines()
        except OSError:
            existing_lines = []
    existing_lines.append(json.dumps(audit_payload, ensure_ascii=False))
    audit_jsonl.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")
    latest_audit_json.write_text(json.dumps(audit_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Apply Next Shadow Experiment Run Results",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- run_id: {summary['run_id']}",
        f"- apply: {str(summary['apply']).lower()}",
        f"- new_candidate_count_after_dedupe: {summary['new_candidate_count_after_dedupe']}",
        f"- duplicate_candidate_skipped_count: {summary['duplicate_candidate_skipped_count']}",
        f"- applied_history_count: {summary['applied_history_count']}",
        f"- applied_tracker_count: {summary['applied_tracker_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create/apply history and tracker deltas from next shadow run results")
    parser.add_argument("--next-run-candidates-csv", default="reports/next_shadow_experiment_run/next_run_candidates.csv")
    parser.add_argument("--next-run-summary-json", default="reports/next_shadow_experiment_run/summary.json")
    parser.add_argument("--experiment-history-csv", default="reports/shadow_experiment_history/experiment_history.csv")
    parser.add_argument("--experiment-sample-tracker-csv", default="reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv")
    parser.add_argument("--next-run-plan-csv", default="reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv")
    parser.add_argument("--output-dir", default="reports/next_shadow_experiment_run_applied")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-shadow-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = apply_next_shadow_experiment_run_results(
        next_run_candidates_csv=str(args.next_run_candidates_csv or "reports/next_shadow_experiment_run/next_run_candidates.csv"),
        next_run_summary_json=str(args.next_run_summary_json or "reports/next_shadow_experiment_run/summary.json"),
        experiment_history_csv=str(args.experiment_history_csv or "reports/shadow_experiment_history/experiment_history.csv"),
        experiment_sample_tracker_csv=str(
            args.experiment_sample_tracker_csv or "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv"
        ),
        next_run_plan_csv=str(args.next_run_plan_csv or "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv"),
        output_dir=str(args.output_dir or "reports/next_shadow_experiment_run_applied"),
        apply=bool(args.apply),
        confirm_shadow_only=bool(args.confirm_shadow_only),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"new_candidate_count_after_dedupe={result.get('new_candidate_count_after_dedupe', 0)}")


if __name__ == "__main__":
    main()
