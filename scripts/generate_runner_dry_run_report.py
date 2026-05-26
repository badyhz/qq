from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import load_candidates
from core.execution_guards import (
    ExecutionGuardError,
    assert_dry_run_required,
    normalize_execution_mode,
)
from scripts.strategy_edge_common import read_csv_rows


FIELDS = [
    "candidate_id",
    "symbol",
    "side",
    "timeframe",
    "candidate_status",
    "gate_decision",
    "submit_allowed",
    "dry_run_allowed",
    "runner_action",
    "block_reason",
    "safety_verdict",
]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def generate_runner_dry_run_report(
    *,
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    gate_audit_jsonl: str = "logs/gate_audit/gate_audit.jsonl",
    gate_replay_csv: str = "reports/gate_replay/gate_replay_results.csv",
    gate_dashboard_json: str = "reports/gate_dashboard/gate_decision_dashboard.json",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    output_dir: str = "reports/runner_dry_run",
) -> dict[str, Any]:
    candidates = load_candidates(candidates_jsonl)
    replay_rows = read_csv_rows(Path(gate_replay_csv))
    gate_dashboard = _load_json(Path(gate_dashboard_json))
    system_health = _load_json(Path(system_health_json))
    _ = gate_audit_jsonl  # input retained for compatibility; replay/dashboard already aggregate gate results.

    replay_index = {str(row.get("candidate_id", "")).strip(): row for row in replay_rows if str(row.get("candidate_id", "")).strip()}

    next_action = str(system_health.get("next_action", "")).strip().upper()
    system_verdict = str(system_health.get("final_verdict", "UNKNOWN")).strip().upper()
    dashboard_verdict = str(gate_dashboard.get("final_verdict", "UNKNOWN")).strip().upper()
    block_low_sample = int(dict(gate_dashboard.get("by_decision", {})).get("BLOCK_LOW_SAMPLE", 0) or 0) > 0
    safety_lock = (
        next_action == "DO_NOT_SUBMIT_TODAY_MAX_DAILY_SUBMITS_REACHED"
        or block_low_sample
        or system_verdict in {"PARTIAL", "FAIL"}
        or dashboard_verdict in {"PARTIAL", "FAIL"}
    )

    rows: list[dict[str, Any]] = []
    approved_candidate_count = 0
    for candidate in candidates:
        current = dict(candidate)
        candidate_id = str(current.get("candidate_id", "")).strip()
        symbol = str(current.get("symbol", "")).strip().upper()
        side = _normalize_side(current.get("side", "BUY"))
        timeframe = str(current.get("timeframe", current.get("signal_timeframe", "5m")) or "5m").strip() or "5m"
        status = str(current.get("status", "")).strip().upper()

        replay = replay_index.get(candidate_id, {})
        gate_decision = str(replay.get("gate_decision", "UNKNOWN")).strip().upper()
        submit_allowed = _to_bool(replay.get("submit_allowed", False))
        dry_run_allowed = _to_bool(replay.get("dry_run_allowed", True))
        reason = str(replay.get("reason", "")).strip()

        runner_action = "UNKNOWN"
        block_reason = reason
        if status != "APPROVED":
            runner_action = "WOULD_SKIP_NOT_APPROVED"
            block_reason = "candidate_not_approved"
        else:
            approved_candidate_count += 1
            if gate_decision.startswith("BLOCK_"):
                runner_action = "WOULD_BLOCK"
                block_reason = reason or gate_decision.lower()
            elif safety_lock:
                runner_action = "WOULD_DRY_RUN_ONLY"
                block_reason = reason or "global_safety_lock"
            elif submit_allowed:
                runner_action = "WOULD_SUBMIT"
                block_reason = ""
            elif dry_run_allowed:
                runner_action = "WOULD_DRY_RUN_ONLY"
                block_reason = reason or "dry_run_only"
            else:
                runner_action = "UNKNOWN"

        safety_verdict = "PASS"
        if runner_action == "WOULD_SUBMIT" and safety_lock:
            safety_verdict = "FAIL"
        rows.append(
            {
                "candidate_id": candidate_id,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "candidate_status": status,
                "gate_decision": gate_decision,
                "submit_allowed": submit_allowed,
                "dry_run_allowed": dry_run_allowed,
                "runner_action": runner_action,
                "block_reason": block_reason,
                "safety_verdict": safety_verdict,
            }
        )

    would_submit_count = sum(1 for row in rows if str(row.get("runner_action", "")).upper() == "WOULD_SUBMIT")
    would_block_count = sum(1 for row in rows if str(row.get("runner_action", "")).upper() == "WOULD_BLOCK")
    would_dry_run_only_count = sum(1 for row in rows if str(row.get("runner_action", "")).upper() == "WOULD_DRY_RUN_ONLY")
    would_skip_not_approved_count = sum(1 for row in rows if str(row.get("runner_action", "")).upper() == "WOULD_SKIP_NOT_APPROVED")
    safety_verdict = "PASS"
    if safety_lock and would_submit_count > 0:
        safety_verdict = "FAIL"

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_json = out_dir / "runner_dry_run_report.json"
    candidates_csv = out_dir / "runner_dry_run_candidates.csv"
    summary_md = out_dir / "summary.md"

    with candidates_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(rows),
        "approved_candidate_count": approved_candidate_count,
        "would_submit_count": would_submit_count,
        "would_block_count": would_block_count,
        "would_dry_run_only_count": would_dry_run_only_count,
        "would_skip_not_approved_count": would_skip_not_approved_count,
        "safety_lock_active": safety_lock,
        "safety_verdict": safety_verdict,
        "system_health_verdict": system_verdict or "UNKNOWN",
        "gate_dashboard_verdict": dashboard_verdict or "UNKNOWN",
        "output_paths": {
            "report_json": str(report_json),
            "candidates_csv": str(candidates_csv),
            "summary_md": str(summary_md),
        },
    }
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Runner Dry Run Report",
        "",
        f"- candidate_count: {report['candidate_count']}",
        f"- approved_candidate_count: {report['approved_candidate_count']}",
        f"- would_submit_count: {report['would_submit_count']}",
        f"- would_block_count: {report['would_block_count']}",
        f"- would_dry_run_only_count: {report['would_dry_run_only_count']}",
        f"- would_skip_not_approved_count: {report['would_skip_not_approved_count']}",
        f"- safety_lock_active: {report['safety_lock_active']}",
        f"- safety_verdict: {report['safety_verdict']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate full-chain runner dry-run report")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--gate-audit-jsonl", default="logs/gate_audit/gate_audit.jsonl")
    parser.add_argument("--gate-replay-csv", default="reports/gate_replay/gate_replay_results.csv")
    parser.add_argument("--gate-dashboard-json", default="reports/gate_dashboard/gate_decision_dashboard.json")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--output-dir", default="reports/runner_dry_run")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    result = generate_runner_dry_run_report(
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        gate_audit_jsonl=str(args.gate_audit_jsonl or "logs/gate_audit/gate_audit.jsonl"),
        gate_replay_csv=str(args.gate_replay_csv or "reports/gate_replay/gate_replay_results.csv"),
        gate_dashboard_json=str(args.gate_dashboard_json or "reports/gate_dashboard/gate_decision_dashboard.json"),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        output_dir=str(args.output_dir or "reports/runner_dry_run"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"would_submit_count={result.get('would_submit_count', 0)}")
    print(f"safety_verdict={result.get('safety_verdict', 'UNKNOWN')}")
    print(f"report_json={result.get('output_paths', {}).get('report_json', '')}")


if __name__ == "__main__":
    main()
