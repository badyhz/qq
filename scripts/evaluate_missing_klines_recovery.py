from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows


FIELDS = [
    "rank",
    "target_report",
    "current_status",
    "required_cache",
    "dependency_status",
    "can_recover_now",
    "recommended_command",
    "reason",
]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _has_missing_snapshot(snapshot_rows: list[dict[str, Any]]) -> bool:
    for row in snapshot_rows:
        status = str(row.get("snapshot_status", "")).strip().upper()
        if status in {"MISSING_KLINES", "PARTIAL"}:
            return True
    return False


def _has_missing_mfe(mfe_rows: list[dict[str, Any]]) -> bool:
    for row in mfe_rows:
        status = str(row.get("analysis_status", "")).strip().upper()
        if status in {"MISSING_KLINES", "PARTIAL"}:
            return True
    return False


def evaluate_missing_klines_recovery(
    *,
    signal_snapshot_csv: str = "reports/signal_snapshot/signal_snapshot.csv",
    post_entry_mfe_mae_csv: str = "reports/post_entry_mfe_mae/post_entry_mfe_mae.csv",
    shadow_collection_summary_json: str = "reports/shadow_candidate_collection/summary.json",
    shadow_outcomes_summary_json: str = "reports/shadow_candidate_outcomes/summary.json",
    kline_cache_backfill_summary_json: str = "reports/kline_cache_backfill/summary.json",
    kline_cache_backfill_plan_csv: str = "reports/kline_cache_backfill_plan/kline_cache_backfill_plan.csv",
    output_dir: str = "reports/missing_klines_recovery",
) -> dict[str, Any]:
    snapshot_rows = read_csv_rows(Path(signal_snapshot_csv))
    mfe_rows = read_csv_rows(Path(post_entry_mfe_mae_csv))
    shadow_collection_summary = _load_json(Path(shadow_collection_summary_json))
    shadow_outcomes_summary = _load_json(Path(shadow_outcomes_summary_json))
    backfill_summary = _load_json(Path(kline_cache_backfill_summary_json))
    backfill_plan_rows = read_csv_rows(Path(kline_cache_backfill_plan_csv))

    backfill_rows_need = [row for row in backfill_plan_rows if str(row.get("cache_status", "")).strip().upper() in {"MISSING", "PARTIAL", "STALE", "UNKNOWN"}]
    backfill_required = len(backfill_rows_need) > 0
    backfill_written = int(backfill_summary.get("written_bars_total", 0) or 0) > 0
    backfill_write_enabled = bool(backfill_summary.get("write_cache", False))
    can_recover_cache = bool(backfill_written and backfill_write_enabled)

    steps = [
        ("run_public_kline_backfill", "run_public_kline_backfill.py"),
        ("signal_snapshot", "generate_signal_snapshot_csv.py"),
        ("post_entry_mfe_mae", "analyze_post_entry_mfe_mae.py"),
        ("tp_sl_efficiency", "evaluate_tp_sl_efficiency.py"),
        ("collect_shadow_candidates", "collect_shadow_candidates.py"),
        ("evaluate_shadow_candidate_outcomes", "evaluate_shadow_candidate_outcomes.py"),
        ("signal_quality", "calculate_signal_quality_score.py"),
        ("strategy_candidate_score", "generate_strategy_candidate_score.py"),
        ("sample_collection_tracker", "update_sample_collection_tracker.py"),
        ("sample_collection_eod_report", "generate_sample_collection_eod_report.py"),
    ]

    rows: list[dict[str, Any]] = []
    for rank, (target, script_name) in enumerate(steps, start=1):
        current_status = "UNKNOWN"
        reason = "status_unknown"
        if target == "run_public_kline_backfill":
            if not backfill_required:
                current_status = "NOT_REQUIRED"
                reason = "cache_already_sufficient"
            elif backfill_summary:
                current_status = "BACKFILL_READY" if can_recover_cache else "BACKFILL_PENDING_WRITE"
                reason = "backfill_written" if can_recover_cache else "dry_run_or_not_executed"
            else:
                current_status = "MISSING_BACKFILL_SUMMARY"
                reason = "missing_backfill_summary"
        elif target == "signal_snapshot":
            current_status = "MISSING_KLINES" if _has_missing_snapshot(snapshot_rows) else ("OK" if snapshot_rows else "MISSING_REPORT")
            reason = "snapshot_needs_klines" if current_status == "MISSING_KLINES" else "snapshot_ready"
        elif target == "post_entry_mfe_mae":
            current_status = "MISSING_KLINES" if _has_missing_mfe(mfe_rows) else ("OK" if mfe_rows else "MISSING_REPORT")
            reason = "mfe_needs_klines" if current_status == "MISSING_KLINES" else "mfe_ready"
        elif target == "collect_shadow_candidates":
            status_reason = str(shadow_collection_summary.get("status_reason", "")).strip().lower()
            if status_reason == "missing_klines":
                current_status = "MISSING_KLINES"
                reason = "collector_missing_klines"
            elif status_reason == "no_new_shadow_candidates":
                current_status = "NO_NEW_CANDIDATES"
                reason = "collector_no_new_candidates"
            elif shadow_collection_summary:
                current_status = "OK"
                reason = "collector_ready"
            else:
                current_status = "MISSING_REPORT"
                reason = "missing_shadow_collection_summary"
        elif target == "evaluate_shadow_candidate_outcomes":
            outcome_reason = str(shadow_outcomes_summary.get("reason", "")).strip().lower()
            if outcome_reason in {"missing_klines", "no_shadow_candidates"}:
                current_status = "PENDING_INPUTS"
                reason = outcome_reason or "no_shadow_candidates"
            elif shadow_outcomes_summary:
                current_status = "OK"
                reason = "shadow_outcomes_ready"
            else:
                current_status = "MISSING_REPORT"
                reason = "missing_shadow_outcomes_summary"
        else:
            current_status = "PENDING_REBUILD"
            reason = "depends_on_previous_steps"

        required_cache = "KLINES_CACHE"
        dependency_status = "READY"
        can_recover_now = True
        if backfill_required and not can_recover_cache:
            dependency_status = "MISSING_BACKFILL"
            can_recover_now = target == "run_public_kline_backfill"
        if target == "run_public_kline_backfill" and backfill_required and not can_recover_cache:
            can_recover_now = True
        if target == "run_public_kline_backfill" and not backfill_required:
            can_recover_now = True

        recommended_command = f"PYTHONPATH=. ./.venv/bin/python scripts/{script_name} --json"
        rows.append(
            {
                "rank": rank,
                "target_report": target,
                "current_status": current_status,
                "required_cache": required_cache,
                "dependency_status": dependency_status,
                "can_recover_now": bool(can_recover_now),
                "recommended_command": recommended_command,
                "reason": reason,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "recovery_steps.csv"
    result_json = out_dir / "missing_klines_recovery.json"
    summary_md = out_dir / "summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    can_recover_all = all(bool(row.get("can_recover_now")) for row in rows)
    result = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if can_recover_all else "PARTIAL",
        "backfill_required": backfill_required,
        "backfill_can_recover_now": can_recover_cache,
        "can_recover_now": can_recover_all,
        "dependency_status": "READY" if can_recover_all else "MISSING_BACKFILL",
        "steps_total": len(rows),
        "steps_recoverable_now": sum(1 for row in rows if bool(row.get("can_recover_now"))),
        "csv_path": str(csv_path),
        "result_json": str(result_json),
        "summary_md": str(summary_md),
    }
    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Missing Klines Recovery",
        "",
        f"- final_verdict: {result['final_verdict']}",
        f"- backfill_required: {result['backfill_required']}",
        f"- backfill_can_recover_now: {result['backfill_can_recover_now']}",
        f"- can_recover_now: {result['can_recover_now']}",
        f"- dependency_status: {result['dependency_status']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate missing-klines recovery readiness and rerun order")
    parser.add_argument("--signal-snapshot-csv", default="reports/signal_snapshot/signal_snapshot.csv")
    parser.add_argument("--post-entry-mfe-mae-csv", default="reports/post_entry_mfe_mae/post_entry_mfe_mae.csv")
    parser.add_argument("--shadow-collection-summary-json", default="reports/shadow_candidate_collection/summary.json")
    parser.add_argument("--shadow-outcomes-summary-json", default="reports/shadow_candidate_outcomes/summary.json")
    parser.add_argument("--kline-cache-backfill-summary-json", default="reports/kline_cache_backfill/summary.json")
    parser.add_argument("--kline-cache-backfill-plan-csv", default="reports/kline_cache_backfill_plan/kline_cache_backfill_plan.csv")
    parser.add_argument("--output-dir", default="reports/missing_klines_recovery")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_missing_klines_recovery(
        signal_snapshot_csv=str(args.signal_snapshot_csv or "reports/signal_snapshot/signal_snapshot.csv"),
        post_entry_mfe_mae_csv=str(args.post_entry_mfe_mae_csv or "reports/post_entry_mfe_mae/post_entry_mfe_mae.csv"),
        shadow_collection_summary_json=str(args.shadow_collection_summary_json or "reports/shadow_candidate_collection/summary.json"),
        shadow_outcomes_summary_json=str(args.shadow_outcomes_summary_json or "reports/shadow_candidate_outcomes/summary.json"),
        kline_cache_backfill_summary_json=str(args.kline_cache_backfill_summary_json or "reports/kline_cache_backfill/summary.json"),
        kline_cache_backfill_plan_csv=str(args.kline_cache_backfill_plan_csv or "reports/kline_cache_backfill_plan/kline_cache_backfill_plan.csv"),
        output_dir=str(args.output_dir or "reports/missing_klines_recovery"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"can_recover_now={result.get('can_recover_now', False)}")


if __name__ == "__main__":
    main()
