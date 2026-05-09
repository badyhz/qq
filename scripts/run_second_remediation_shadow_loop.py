from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Safety tokens — anything containing these in a command will be blocked
UNSAFE_TOKENS = [
    "allow-testnet-submit",
    "submit-approved",
    "submit_replayed",
    "cancel",
    "flatten",
    "/fapi/v1/order",
    "/fapi/v1/algoorder",
    "delete",
    "post",
]

STEP_FIELDS = [
    "step",
    "name",
    "action_type",
    "command",
    "status",
    "return_code",
    "expected_output_exists",
    "output_summary",
    "error",
]


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
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader if row]
    except (OSError, csv.Error):
        return []


def _is_unsafe(command: str) -> bool:
    text = command.strip().lower()
    return any(token in text for token in UNSAFE_TOKENS)


def _read_sample_gap() -> int:
    report = _read_json(Path("reports/daily_shadow_research_control/daily_shadow_research_control_report.json"))
    raw = report.get("sample_gap_total", 0)
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return 0


def _read_int_from_summary(path: Path, key: str) -> int:
    payload = _read_json(path)
    raw = payload.get(key, 0)
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return 0


def _collect_missing_inputs(
    *,
    remediation_loop_packet_json: str,
    remediation_history_csv: str,
    first_loop_report_json: str,
    shadow_outcomes_summary_json: str,
    sample_targets_summary_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("remediation_loop_packet_json", Path(remediation_loop_packet_json)),
        ("remediation_history_csv", Path(remediation_history_csv)),
        ("first_loop_report_json", Path(first_loop_report_json)),
        ("shadow_outcomes_summary_json", Path(shadow_outcomes_summary_json)),
        ("sample_targets_summary_json", Path(sample_targets_summary_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def run_second_remediation_shadow_loop(
    *,
    remediation_loop_packet_json: str = "reports/remediation_loop_packet/remediation_loop_packet.json",
    remediation_history_csv: str = "reports/remediation_loop_history/remediation_loop_history.csv",
    first_loop_report_json: str = "reports/remediation_loop_run/remediation_loop_run_report.json",
    shadow_outcomes_summary_json: str = "reports/shadow_candidate_outcomes/summary.json",
    sample_targets_summary_json: str = "reports/shadow_sample_targets/summary.json",
    output_dir: str = "reports/second_remediation_loop",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        remediation_loop_packet_json=remediation_loop_packet_json,
        remediation_history_csv=remediation_history_csv,
        first_loop_report_json=first_loop_report_json,
        shadow_outcomes_summary_json=shadow_outcomes_summary_json,
        sample_targets_summary_json=sample_targets_summary_json,
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Safety flags — always false in this phase
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False
    testnet_submit_allowed = False
    real_submit_allowed = False
    allowed_mode = "SHADOW_ONLY"
    submit_permission = "NO_SUBMIT"

    second_loop_run_id = f"SECOND_REMEDIATION_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    # Read history
    history_rows = _read_csv_rows(Path(remediation_history_csv))
    source_history_runs = len(history_rows)

    # Read first-loop report
    first_loop = _read_json(Path(first_loop_report_json))
    first_loop_gap_after = first_loop.get("sample_gap_after", 0)
    try:
        first_loop_gap_after = int(float(first_loop_gap_after))
    except (TypeError, ValueError):
        first_loop_gap_after = 0

    # Read packet commands
    packet = _read_json(Path(remediation_loop_packet_json))
    commands = packet.get("commands", [])
    if not isinstance(commands, list):
        commands = []

    sample_gap_before = _read_sample_gap()
    if sample_gap_before == 0 and first_loop_gap_after > 0:
        sample_gap_before = first_loop_gap_after

    rows: list[dict[str, Any]] = []
    steps_passed = 0
    steps_partial = 0
    steps_failed = 0
    blocked = False
    failed_verdict = "PASS"

    for index, entry in enumerate(commands, start=1):
        step = int(entry.get("step", index) or index)
        name = str(entry.get("name", "")).strip() or f"step_{step}"
        action_type = str(entry.get("action_type", "UNKNOWN")).strip().upper() or "UNKNOWN"
        command = str(entry.get("command", "")).strip()
        expected_outputs = entry.get("expected_outputs", [])
        if not isinstance(expected_outputs, list):
            expected_outputs = []
        stop_on_failure = bool(entry.get("stop_on_failure", True))

        row = {
            "step": step,
            "name": name,
            "action_type": action_type,
            "command": command,
            "status": "PASS",
            "return_code": 0,
            "expected_output_exists": True,
            "output_summary": "",
            "error": "",
        }

        if _is_unsafe(command):
            row["status"] = "FAIL"
            row["return_code"] = -1
            row["expected_output_exists"] = False
            row["error"] = "unsafe_command_detected"
            row["output_summary"] = "blocked_before_execution"
            rows.append(row)
            steps_failed += 1
            blocked = True
            failed_verdict = "FAIL"
            break

        if not command:
            row["status"] = "PASS"
            row["return_code"] = 0
            row["expected_output_exists"] = True
            row["output_summary"] = "noop_empty_command"
            rows.append(row)
            steps_passed += 1
            continue

        try:
            env = os.environ.copy()
            env.setdefault("ALLOWED_MODE", "SHADOW_ONLY")
            env.setdefault("SUBMIT_PERMISSION", "NO_SUBMIT")
            proc = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )
            row["return_code"] = int(proc.returncode)
            output_excerpt = (proc.stdout or "").strip().splitlines()[:3]
            if not output_excerpt:
                output_excerpt = ((proc.stderr or "").strip().splitlines()[:3]) or [""]
            row["output_summary"] = " | ".join(part for part in output_excerpt if part).strip()

            exists = True
            for output_path in expected_outputs:
                if not str(output_path).strip():
                    continue
                if not Path(str(output_path)).exists():
                    exists = False
                    break
            row["expected_output_exists"] = bool(exists)

            if proc.returncode != 0:
                row["status"] = "FAIL"
                row["error"] = "command_failed"
                steps_failed += 1
                rows.append(row)
                if stop_on_failure:
                    failed_verdict = "FAIL"
                    break
                continue
            if not exists:
                row["status"] = "PARTIAL"
                row["error"] = "expected_output_missing"
                steps_partial += 1
            else:
                row["status"] = "PASS"
                steps_passed += 1
        except subprocess.TimeoutExpired:
            row["status"] = "FAIL"
            row["return_code"] = -2
            row["expected_output_exists"] = False
            row["error"] = "command_timeout"
            row["output_summary"] = "timeout"
            steps_failed += 1
            rows.append(row)
            failed_verdict = "FAIL"
            break
        rows.append(row)

    sample_gap_after = _read_sample_gap()
    if sample_gap_after == 0 and sample_gap_before > 0:
        sample_gap_after = sample_gap_before

    # Detect new shadow samples
    shadow_outcomes = _read_json(Path(shadow_outcomes_summary_json))
    new_shadow_samples_detected = int(shadow_outcomes.get("shadow_sample_count", 0) or 0)

    # Detect new experiment candidates
    next_run_summary = Path("reports/next_shadow_experiment_run/summary.json")
    new_experiment_candidates = _read_int_from_summary(next_run_summary, "next_run_candidate_count")
    if new_experiment_candidates <= 0:
        new_experiment_candidates = _read_int_from_summary(next_run_summary, "experiment_candidate_count")

    # Determine remediation effectiveness
    remediation_effective = False
    if sample_gap_after < sample_gap_before and steps_passed > 0:
        remediation_effective = True

    still_not_ready = True
    if sample_gap_after == 0 and remediation_effective:
        still_not_ready = False

    # Final verdict
    final_verdict = "PASS"
    if blocked or steps_failed > 0:
        final_verdict = "FAIL"
    elif steps_partial > 0:
        final_verdict = "PARTIAL"
    elif missing_inputs:
        final_verdict = "PARTIAL"

    if failed_verdict == "FAIL":
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T366",
        "phase": "SHADOW_ONLY_REMEDIATION_ROUND_2",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "second_loop_run_id": second_loop_run_id,
        "source_history_runs": source_history_runs,
        "new_shadow_samples_detected": max(0, new_shadow_samples_detected),
        "new_experiment_candidates": max(0, new_experiment_candidates),
        "sample_gap_before": sample_gap_before,
        "sample_gap_after": sample_gap_after,
        "remediation_effective": remediation_effective,
        "still_not_ready": still_not_ready,
        "final_verdict": final_verdict,
        "missing_inputs": missing_inputs,
        "steps_total": len(rows),
        "steps_passed": steps_passed,
        "steps_partial": steps_partial,
        "steps_failed": steps_failed,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "second_remediation_loop_report.json"
    steps_csv = out_dir / "step_results.csv"
    summary_md = out_dir / "summary.md"

    with steps_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STEP_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in STEP_FIELDS})

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Second Remediation Shadow-Only Loop",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- second_loop_run_id: {report['second_loop_run_id']}",
        f"- source_history_runs: {report['source_history_runs']}",
        f"- new_shadow_samples_detected: {report['new_shadow_samples_detected']}",
        f"- new_experiment_candidates: {report['new_experiment_candidates']}",
        f"- sample_gap_before: {report['sample_gap_before']}",
        f"- sample_gap_after: {report['sample_gap_after']}",
        f"- remediation_effective: {report['remediation_effective']}",
        f"- still_not_ready: {report['still_not_ready']}",
        f"- steps_total: {report['steps_total']}",
        f"- steps_passed: {report['steps_passed']}",
        f"- steps_partial: {report['steps_partial']}",
        f"- steps_failed: {report['steps_failed']}",
        f"- missing_inputs: {report['missing_inputs']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run second remediation shadow-only loop")
    parser.add_argument("--remediation-loop-packet-json", default="reports/remediation_loop_packet/remediation_loop_packet.json")
    parser.add_argument("--remediation-history-csv", default="reports/remediation_loop_history/remediation_loop_history.csv")
    parser.add_argument("--first-loop-report-json", default="reports/remediation_loop_run/remediation_loop_run_report.json")
    parser.add_argument("--shadow-outcomes-summary-json", default="reports/shadow_candidate_outcomes/summary.json")
    parser.add_argument("--sample-targets-summary-json", default="reports/shadow_sample_targets/summary.json")
    parser.add_argument("--output-dir", default="reports/second_remediation_loop")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_second_remediation_shadow_loop(
        remediation_loop_packet_json=str(args.remediation_loop_packet_json or "reports/remediation_loop_packet/remediation_loop_packet.json"),
        remediation_history_csv=str(args.remediation_history_csv or "reports/remediation_loop_history/remediation_loop_history.csv"),
        first_loop_report_json=str(args.first_loop_report_json or "reports/remediation_loop_run/remediation_loop_run_report.json"),
        shadow_outcomes_summary_json=str(args.shadow_outcomes_summary_json or "reports/shadow_candidate_outcomes/summary.json"),
        sample_targets_summary_json=str(args.sample_targets_summary_json or "reports/shadow_sample_targets/summary.json"),
        output_dir=str(args.output_dir or "reports/second_remediation_loop"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"second_loop_run_id={result.get('second_loop_run_id','')}")
    print(f"remediation_effective={result.get('remediation_effective',False)}")
    print(f"still_not_ready={result.get('still_not_ready',True)}")


if __name__ == "__main__":
    main()
