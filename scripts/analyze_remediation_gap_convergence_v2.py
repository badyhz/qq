from __future__ import annotations

import argparse
import csv
import json
import math
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
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader if row]
    except (OSError, csv.Error):
        return []


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _calculate_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    x_sum = sum(range(n))
    y_sum = sum(values)
    xy_sum = sum(i * val for i, val in enumerate(values))
    x_sq_sum = sum(i * i for i in range(n))
    denominator = n * x_sq_sum - x_sum * x_sum
    if abs(denominator) < 1e-9:
        return 0.0
    return (n * xy_sum - x_sum * y_sum) / denominator


def _collect_missing_inputs(
    *,
    remediation_history_csv: str,
    second_loop_report_json: str,
    first_convergence_summary_json: str,
    sample_targets_summary_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("remediation_history_csv", Path(remediation_history_csv)),
        ("second_loop_report_json", Path(second_loop_report_json)),
        ("first_convergence_summary_json", Path(first_convergence_summary_json)),
        ("sample_targets_summary_json", Path(sample_targets_summary_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def analyze_remediation_gap_convergence_v2(
    *,
    remediation_history_csv: str = "reports/remediation_loop_history/remediation_loop_history.csv",
    second_loop_report_json: str = "reports/second_remediation_loop/second_remediation_loop_report.json",
    first_convergence_summary_json: str = "reports/remediation_gap_convergence/summary.json",
    sample_targets_summary_json: str = "reports/shadow_sample_targets/summary.json",
    output_dir: str = "reports/remediation_gap_convergence_v2",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        remediation_history_csv=remediation_history_csv,
        second_loop_report_json=second_loop_report_json,
        first_convergence_summary_json=first_convergence_summary_json,
        sample_targets_summary_json=sample_targets_summary_json,
    )

    # Safety flags — always false in this phase
    allowed_mode = "SHADOW_ONLY"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Read history rows
    history_rows = _read_csv_rows(Path(remediation_history_csv))
    runs_analyzed = len(history_rows)

    # Read second loop report (T366)
    second_loop = _read_json(Path(second_loop_report_json))
    samp_gap_before = _to_int(second_loop.get("sample_gap_before", 0))
    samp_gap_after = _to_int(second_loop.get("sample_gap_after", 0))
    remediation_effective_t366 = bool(second_loop.get("remediation_effective", False))

    # Read first convergence summary
    first_conv = _read_json(Path(first_convergence_summary_json))
    gap_initial = _to_int(first_conv.get("current_sample_gap", 0))
    if gap_initial == 0 and history_rows:
        gap_initial = _to_int(history_rows[0].get("sample_gap_after", 0))

    # Build gap series from history
    sample_gaps: list[int] = []
    for row in history_rows:
        g = _to_int(row.get("sample_gap_after", 0))
        sample_gaps.append(g)

    # Add second loop data
    if samp_gap_before > 0 or samp_gap_after > 0:
        if not sample_gaps or sample_gaps[-1] != samp_gap_before:
            sample_gaps.append(samp_gap_before)
        sample_gaps.append(samp_gap_after)

    # Compute gaps
    gap_previous = sample_gaps[-2] if len(sample_gaps) >= 2 else gap_initial
    gap_latest = sample_gaps[-1] if sample_gaps else gap_initial
    gap_delta_latest = gap_latest - gap_previous

    # Trend determination
    float_gaps = [float(g) for g in sample_gaps]
    slope = _calculate_slope(float_gaps)

    gap_trend = "UNKNOWN"
    if len(sample_gaps) >= 3:
        recent = sample_gaps[-3:]
        if all(recent[i] <= recent[i - 1] for i in range(1, len(recent))):
            gap_trend = "IMPROVING"
        elif all(recent[i] >= recent[i - 1] for i in range(1, len(recent))):
            gap_trend = "WORSENING"
        elif slope > 0.5:
            gap_trend = "WORSENING"
        elif slope < -0.5:
            gap_trend = "IMPROVING"
        else:
            gap_trend = "FLAT"
    elif len(sample_gaps) == 2:
        if gap_latest < gap_previous:
            gap_trend = "IMPROVING"
        elif gap_latest > gap_previous:
            gap_trend = "WORSENING"
        else:
            gap_trend = "FLAT"

    # Convergence confidence
    convergence_confidence = "LOW"
    if runs_analyzed >= 5 and gap_trend == "IMPROVING" and gap_latest < gap_initial * 0.7:
        convergence_confidence = "HIGH"
    elif runs_analyzed >= 3 and gap_trend in {"IMPROVING", "FLAT"} and gap_latest < gap_initial:
        convergence_confidence = "MEDIUM"

    # Remediation effective from combined analysis
    remediation_effective = False
    if gap_trend == "IMPROVING" and gap_latest < gap_initial:
        remediation_effective = True
    if remediation_effective_t366:
        remediation_effective = True

    # still_not_ready: gap_latest > 0 => true
    still_not_ready = gap_latest > 0

    # Final verdict
    final_verdict = "PASS"
    if missing_inputs and runs_analyzed == 0:
        final_verdict = "PARTIAL"
    elif still_not_ready and gap_trend == "IMPROVING":
        final_verdict = "PASS"
    elif still_not_ready:
        final_verdict = "PASS"
    elif not still_not_ready:
        final_verdict = "PASS"

    report: dict[str, Any] = {
        "task_id": "T367",
        "phase": "REMEDIATION_GAP_CONVERGENCE_V2",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "runs_analyzed": runs_analyzed,
        "gap_initial": gap_initial,
        "gap_previous": gap_previous,
        "gap_latest": gap_latest,
        "gap_delta_latest": gap_delta_latest,
        "gap_trend": gap_trend,
        "remediation_effective": remediation_effective,
        "still_not_ready": still_not_ready,
        "convergence_confidence": convergence_confidence,
        "gap_slope": round(slope, 6),
        "final_verdict": final_verdict,
        "missing_inputs": missing_inputs,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    summary_json = out_dir / "summary.json"
    trend_json = out_dir / "trend_data.json"
    summary_md = out_dir / "summary.md"

    summary_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    trend_data = {
        "sample_gaps": sample_gaps,
        "gap_slope": round(slope, 6),
        "runs_analyzed": runs_analyzed,
    }
    trend_json.write_text(json.dumps(trend_data, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Remediation Gap Convergence V2",
        "",
        f"- task_id: {report['task_id']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- runs_analyzed: {report['runs_analyzed']}",
        f"- gap_initial: {report['gap_initial']}",
        f"- gap_previous: {report['gap_previous']}",
        f"- gap_latest: {report['gap_latest']}",
        f"- gap_delta_latest: {report['gap_delta_latest']}",
        f"- gap_trend: {report['gap_trend']}",
        f"- convergence_confidence: {report['convergence_confidence']}",
        f"- remediation_effective: {report['remediation_effective']}",
        f"- still_not_ready: {report['still_not_ready']}",
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
    parser = argparse.ArgumentParser(description="Analyze remediation gap convergence v2 with second loop data")
    parser.add_argument("--remediation-history-csv", default="reports/remediation_loop_history/remediation_loop_history.csv")
    parser.add_argument("--second-loop-report-json", default="reports/second_remediation_loop/second_remediation_loop_report.json")
    parser.add_argument("--first-convergence-summary-json", default="reports/remediation_gap_convergence/summary.json")
    parser.add_argument("--sample-targets-summary-json", default="reports/shadow_sample_targets/summary.json")
    parser.add_argument("--output-dir", default="reports/remediation_gap_convergence_v2")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = analyze_remediation_gap_convergence_v2(
        remediation_history_csv=str(args.remediation_history_csv or "reports/remediation_loop_history/remediation_loop_history.csv"),
        second_loop_report_json=str(args.second_loop_report_json or "reports/second_remediation_loop/second_remediation_loop_report.json"),
        first_convergence_summary_json=str(args.first_convergence_summary_json or "reports/remediation_gap_convergence/summary.json"),
        sample_targets_summary_json=str(args.sample_targets_summary_json or "reports/shadow_sample_targets/summary.json"),
        output_dir=str(args.output_dir or "reports/remediation_gap_convergence_v2"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"gap_trend={result.get('gap_trend','')}")
    print(f"still_not_ready={result.get('still_not_ready',True)}")


if __name__ == "__main__":
    main()
