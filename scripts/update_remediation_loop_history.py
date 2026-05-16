from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(dict(row))
    except (OSError, csv.Error):
        pass
    return rows


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _parse_source_time(value: Any, fallback: datetime) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def update_remediation_loop_history(
    *,
    remediation_loop_run_report_json: str = "reports/remediation_loop_run/remediation_loop_run_report.json",
    remediation_result_json: str = "reports/remediation_result/remediation_result.json",
    phase_control_v2_json: str = "reports/phase_control/phase_control_report_v2.json",
    output_dir: str = "reports/remediation_loop_history",
    rebuild: bool = False,
) -> dict[str, Any]:
    run_report = _read_json(Path(remediation_loop_run_report_json))
    remediation_result = _read_json(Path(remediation_result_json))
    phase_v2 = _read_json(Path(phase_control_v2_json))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "remediation_loop_history.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"

    existing_rows = [] if rebuild else _read_csv_rows(csv_path)
    now = datetime.now(timezone.utc)
    source_time = _parse_source_time(run_report.get("generated_at_utc"), now)
    run_id = f"remediation_loop_{source_time.strftime('%Y%m%d_%H%M%S')}"

    # Safety: ensure no submit attempts in history
    steps_total = int(run_report.get("steps_total", 0) or 0)
    steps_passed = int(run_report.get("steps_passed", 0) or 0)
    steps_failed = int(run_report.get("steps_failed", 0) or 0)
    new_candidates = int(run_report.get("new_experiment_candidates", 0) or 0)
    sample_gap_before = int(run_report.get("sample_gap_before", 0) or 0)
    sample_gap_after = int(run_report.get("sample_gap_after", 0) or 0)
    gap_delta = int(run_report.get("gap_delta", 0) or 0)

    row = {
        "run_id": run_id,
        "run_date": source_time.date().isoformat(),
        "run_time": source_time.strftime("%H:%M:%S"),
        "source_generated_at_utc": source_time.isoformat(),
        "current_phase": str(phase_v2.get("current_phase", "SHADOW_EXPERIMENT_REMEDIATION")).strip().upper() or "SHADOW_EXPERIMENT_REMEDIATION",
        "steps_total": steps_total,
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "new_candidates_collected": max(0, new_candidates),
        "sample_gap_before": sample_gap_before,
        "sample_gap_after": sample_gap_after,
        "gap_delta": gap_delta,
        "remediation_effective": bool(remediation_result.get("remediation_effective", False)),
        "recommended_next_action": str(remediation_result.get("recommended_next_action", "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP")).strip().upper() or "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP",
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "created_at": now.isoformat(),
    }

    # Append new run only if we have meaningful data
    appended = False
    updated_existing = False
    if steps_total > 0 or new_candidates > 0:
        existing_index = next((idx for idx, existing in enumerate(existing_rows) if str(existing.get("run_id", "")) == run_id), None)
        if existing_index is None:
            existing_rows.append(row)
            appended = True
        else:
            existing_rows[existing_index] = row
            updated_existing = True

    # Sort by run_id for deterministic output
    existing_rows.sort(key=lambda item: str(item.get("run_id", "")))

    fields = [
        "run_id",
        "run_date",
        "run_time",
        "source_generated_at_utc",
        "current_phase",
        "steps_total",
        "steps_passed",
        "steps_failed",
        "new_candidates_collected",
        "sample_gap_before",
        "sample_gap_after",
        "gap_delta",
        "remediation_effective",
        "recommended_next_action",
        "submit_attempted",
        "cancel_attempted",
        "flatten_attempted",
        "created_at",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row_item in existing_rows:
            # Ensure safety fields are always false
            row_item["submit_attempted"] = False
            row_item["cancel_attempted"] = False
            row_item["flatten_attempted"] = False
            writer.writerow({field: row_item.get(field, "") for field in fields})

    # Calculate stats for summary
    total_runs = len(existing_rows)
    total_candidates = sum(int(_to_int(r.get("new_candidates_collected", 0))) for r in existing_rows)
    total_gap_delta = sum(int(_to_int(r.get("gap_delta", 0))) for r in existing_rows)
    effective_runs = sum(1 for r in existing_rows if str(r.get("remediation_effective", "")).lower() in {"true", "1", "yes"})

    summary = {
        "generated_at_utc": now.isoformat(),
        "final_verdict": "PASS" if existing_rows else "PARTIAL",
        "rebuild": bool(rebuild),
        "appended": bool(appended),
        "updated_existing": bool(updated_existing),
        "total_runs": total_runs,
        "effective_runs": effective_runs,
        "total_candidates_collected": max(0, total_candidates),
        "total_gap_delta": total_gap_delta,
        "latest_run_id": str(existing_rows[-1].get("run_id", "")) if existing_rows else "",
        "latest_sample_gap_after": int(_to_int(existing_rows[-1].get("sample_gap_after", 0))) if existing_rows else 0,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "allowed_mode": "SHADOW_ONLY",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }

    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Remediation Loop History",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_runs: {summary['total_runs']}",
        f"- effective_runs: {summary['effective_runs']}",
        f"- total_candidates_collected: {summary['total_candidates_collected']}",
        f"- total_gap_delta: {summary['total_gap_delta']}",
        "- allowed_mode: SHADOW_ONLY",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track remediation loop multi-run history")
    parser.add_argument("--remediation-loop-run-report-json", default="reports/remediation_loop_run/remediation_loop_run_report.json")
    parser.add_argument("--remediation-result-json", default="reports/remediation_result/remediation_result.json")
    parser.add_argument("--phase-control-v2-json", default="reports/phase_control/phase_control_report_v2.json")
    parser.add_argument("--output-dir", default="reports/remediation_loop_history")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = update_remediation_loop_history(
        remediation_loop_run_report_json=str(
            args.remediation_loop_run_report_json or "reports/remediation_loop_run/remediation_loop_run_report.json"
        ),
        remediation_result_json=str(args.remediation_result_json or "reports/remediation_result/remediation_result.json"),
        phase_control_v2_json=str(args.phase_control_v2_json or "reports/phase_control/phase_control_report_v2.json"),
        output_dir=str(args.output_dir or "reports/remediation_loop_history"),
        rebuild=bool(args.rebuild),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"total_runs={result.get('total_runs', 0)}")


if __name__ == "__main__":
    main()
