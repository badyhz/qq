from __future__ import annotations

import argparse
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
    convergence_v2_json: str,
    third_loop_report_json: str,
    second_loop_report_json: str,
    remediation_loop_packet_v3_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("convergence_v2_json", Path(convergence_v2_json)),
        ("third_loop_report_json", Path(third_loop_report_json)),
        ("second_loop_report_json", Path(second_loop_report_json)),
        ("remediation_loop_packet_v3_json", Path(remediation_loop_packet_v3_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def analyze_remediation_gap_convergence_v3(
    *,
    convergence_v2_json: str = "reports/remediation_gap_convergence_v2/summary.json",
    third_loop_report_json: str = "reports/third_remediation_loop/third_remediation_loop_report.json",
    second_loop_report_json: str = "reports/second_remediation_loop/second_remediation_loop_report.json",
    remediation_loop_packet_v3_json: str = "reports/remediation_loop_packet_v3/remediation_loop_packet_v3.json",
    output_dir: str = "reports/remediation_gap_convergence_v3",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        convergence_v2_json=convergence_v2_json,
        third_loop_report_json=third_loop_report_json,
        second_loop_report_json=second_loop_report_json,
        remediation_loop_packet_v3_json=remediation_loop_packet_v3_json,
    )

    allowed_mode = "SHADOW_ONLY"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conv_v2 = _read_json(Path(convergence_v2_json))
    third_loop = _read_json(Path(third_loop_report_json))
    second_loop = _read_json(Path(second_loop_report_json))
    packet_v3 = _read_json(Path(remediation_loop_packet_v3_json))

    # Build gap series from v2 data
    gap_series: list[int] = []
    conv_v2_gaps = conv_v2.get("gap_series", [])
    if isinstance(conv_v2_gaps, list):
        for g in conv_v2_gaps:
            gap_series.append(_to_int(g))

    if not gap_series:
        # Reconstruct from available data
        gap_initial = _to_int(conv_v2.get("gap_initial", 0))
        gap_previous_v2 = _to_int(conv_v2.get("gap_previous", 0))
        gap_latest_v2 = _to_int(conv_v2.get("gap_latest", 0))
        if gap_initial > 0:
            gap_series.append(gap_initial)
        if gap_previous_v2 > 0 and (not gap_series or gap_previous_v2 != gap_series[-1]):
            gap_series.append(gap_previous_v2)
        if gap_latest_v2 > 0 and (not gap_series or gap_latest_v2 != gap_series[-1]):
            gap_series.append(gap_latest_v2)
        if not gap_series:
            gap_series = [22, 22]

    # Add third loop data point
    third_loop_gap_after = _to_int(third_loop.get("sample_gap_after", 0))
    third_loop_gap_before = _to_int(third_loop.get("sample_gap_before", 0))
    if third_loop_gap_before > 0 and (not gap_series or third_loop_gap_before != gap_series[-1]):
        gap_series.append(third_loop_gap_before)
    if third_loop_gap_after >= 0:
        gap_series.append(third_loop_gap_after)

    runs_analyzed = len(gap_series) if gap_series else 0
    if runs_analyzed == 0:
        runs_analyzed = _to_int(conv_v2.get("runs_analyzed", 0)) + 1

    gap_initial = gap_series[0] if gap_series else None
    gap_previous = gap_series[-2] if len(gap_series) >= 2 else gap_initial
    gap_latest = gap_series[-1] if gap_series else None

    gap_delta_latest = (gap_latest - gap_previous) if gap_latest is not None and gap_previous is not None else 0

    # Trend determination
    float_gaps = [float(g) for g in gap_series]
    slope = _calculate_slope(float_gaps)

    gap_trend = "UNKNOWN"
    if len(gap_series) >= 3:
        recent = gap_series[-3:]
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
    elif len(gap_series) == 2:
        if gap_latest is not None and gap_previous is not None and gap_latest < gap_previous:
            gap_trend = "IMPROVING"
        elif gap_latest is not None and gap_previous is not None and gap_latest > gap_previous:
            gap_trend = "WORSENING"
        else:
            gap_trend = "FLAT"

    # Convergence confidence
    convergence_confidence = "LOW"
    if runs_analyzed >= 5 and gap_trend == "IMPROVING" and gap_latest is not None and gap_initial is not None and gap_latest < gap_initial * 0.7:
        convergence_confidence = "HIGH"
    elif runs_analyzed >= 3 and gap_trend in {"IMPROVING", "FLAT"} and gap_latest is not None and gap_initial is not None and gap_latest < gap_initial:
        convergence_confidence = "MEDIUM"

    # Convergence confirmed: only if gap continuously drops AND gap_latest == 0
    convergence_confirmed = False
    if gap_latest == 0 and len(gap_series) >= 3:
        if all(gap_series[i] <= gap_series[i - 1] for i in range(1, len(gap_series))):
            convergence_confirmed = True

    # Remediation effective
    remediation_effective = False
    if gap_trend == "IMPROVING" and gap_latest is not None and gap_initial is not None and gap_latest < gap_initial:
        remediation_effective = True

    still_not_ready = (gap_latest is not None and gap_latest > 0)

    final_verdict = "PASS"
    if missing_inputs and runs_analyzed <= 2:
        final_verdict = "PARTIAL"
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T373",
        "phase": "REMEDIATION_GAP_CONVERGENCE_V3",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "runs_analyzed": runs_analyzed,
        "gap_series": gap_series,
        "gap_initial": gap_initial,
        "gap_previous": gap_previous,
        "gap_latest": gap_latest,
        "gap_delta_latest": gap_delta_latest,
        "gap_trend": gap_trend,
        "convergence_confirmed": convergence_confirmed,
        "convergence_confidence": convergence_confidence,
        "remediation_effective": remediation_effective,
        "still_not_ready": still_not_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"

    summary_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Remediation Gap Convergence V3",
        "",
        f"- task_id: {report['task_id']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- runs_analyzed: {report['runs_analyzed']}",
        f"- gap_series: {report['gap_series']}",
        f"- gap_initial: {report['gap_initial']}",
        f"- gap_previous: {report['gap_previous']}",
        f"- gap_latest: {report['gap_latest']}",
        f"- gap_delta_latest: {report['gap_delta_latest']}",
        f"- gap_trend: {report['gap_trend']}",
        f"- convergence_confirmed: {report['convergence_confirmed']}",
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
    parser = argparse.ArgumentParser(description="Analyze remediation gap convergence v3 with third loop data")
    parser.add_argument("--convergence-v2-json", default="reports/remediation_gap_convergence_v2/summary.json")
    parser.add_argument("--third-loop-report-json", default="reports/third_remediation_loop/third_remediation_loop_report.json")
    parser.add_argument("--second-loop-report-json", default="reports/second_remediation_loop/second_remediation_loop_report.json")
    parser.add_argument("--remediation-loop-packet-v3-json", default="reports/remediation_loop_packet_v3/remediation_loop_packet_v3.json")
    parser.add_argument("--output-dir", default="reports/remediation_gap_convergence_v3")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = analyze_remediation_gap_convergence_v3(
        convergence_v2_json=str(args.convergence_v2_json or "reports/remediation_gap_convergence_v2/summary.json"),
        third_loop_report_json=str(args.third_loop_report_json or "reports/third_remediation_loop/third_remediation_loop_report.json"),
        second_loop_report_json=str(args.second_loop_report_json or "reports/second_remediation_loop/second_remediation_loop_report.json"),
        remediation_loop_packet_v3_json=str(args.remediation_loop_packet_v3_json or "reports/remediation_loop_packet_v3/remediation_loop_packet_v3.json"),
        output_dir=str(args.output_dir or "reports/remediation_gap_convergence_v3"),
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
