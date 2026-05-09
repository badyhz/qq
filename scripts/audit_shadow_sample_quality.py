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


def _collect_missing_inputs(
    *,
    shadow_sample_quality_json: str,
    shadow_candidate_outcomes_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("shadow_sample_quality_json", Path(shadow_sample_quality_json)),
        ("shadow_candidate_outcomes_json", Path(shadow_candidate_outcomes_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def audit_shadow_sample_quality(
    *,
    shadow_sample_quality_json: str = "reports/shadow_sample_quality/shadow_sample_quality_dashboard.json",
    shadow_candidate_outcomes_json: str = "reports/shadow_candidate_outcomes/summary.json",
    output_dir: str = "reports/shadow_sample_quality_audit",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_sample_quality_json=shadow_sample_quality_json,
        shadow_candidate_outcomes_json=shadow_candidate_outcomes_json,
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

    sample_quality = _read_json(Path(shadow_sample_quality_json))
    shadow_outcomes = _read_json(Path(shadow_candidate_outcomes_json))

    samples_analyzed = 0
    unique_sample_keys = 0
    duplicate_samples = 0
    missing_required_fields_count = 0
    timestamp_anomaly_count = 0
    symbol_coverage_count = 0
    timeframe_coverage_count = 0
    quality_score = 0.0
    quality_grade = "UNKNOWN"
    sample_quality_ready = False
    audit_warnings: list[str] = []

    # Extract from sample quality dashboard
    if sample_quality:
        samples_analyzed = sample_quality.get("total_samples", 0) or 0
        unique_sample_keys = sample_quality.get("unique_samples", 0) or 0
        duplicate_samples = sample_quality.get("duplicate_samples", 0) or 0
        missing_required_fields_count = sample_quality.get("missing_fields", 0) or 0
        timestamp_anomaly_count = sample_quality.get("timestamp_anomalies", 0) or 0
        symbol_coverage_count = sample_quality.get("symbol_coverage", 0) or 0
        timeframe_coverage_count = sample_quality.get("timeframe_coverage", 0) or 0
        quality_score = sample_quality.get("quality_score", 0.0) or 0.0

    # Extract from shadow outcomes as fallback
    if samples_analyzed == 0 and shadow_outcomes:
        samples_analyzed = shadow_outcomes.get("shadow_sample_count", 0) or 0
        unique_sample_keys = samples_analyzed

    # Determine quality grade
    if samples_analyzed == 0:
        quality_grade = "UNKNOWN"
        audit_warnings.append("no_samples_available")
    elif duplicate_samples > 0 or missing_required_fields_count > 0:
        if duplicate_samples <= 2 and missing_required_fields_count <= 2:
            quality_grade = "FAIR"
        else:
            quality_grade = "POOR"
        audit_warnings.append("quality_issues_detected")
    else:
        quality_grade = "GOOD"
        quality_score = min(100.0, max(0.0, quality_score or 0.0))

    # Determine if sample quality is ready
    sample_quality_ready = False
    if samples_analyzed > 0:
        if duplicate_samples == 0 and missing_required_fields_count == 0:
            if quality_grade == "GOOD":
                sample_quality_ready = True

    # Determine final verdict
    final_verdict = "PASS"
    if quality_grade == "POOR":
        final_verdict = "FAIL"
    elif missing_inputs or quality_grade in {"UNKNOWN", "FAIR"}:
        final_verdict = "PARTIAL"

    # Safety overrides
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        audit_warnings.append("safety_flags_abnormal")

    report: dict[str, Any] = {
        "task_id": "T376",
        "phase": "SHADOW_SAMPLE_QUALITY_AUDIT",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "samples_analyzed": samples_analyzed,
        "unique_sample_keys": unique_sample_keys,
        "duplicate_samples": duplicate_samples,
        "missing_required_fields_count": missing_required_fields_count,
        "timestamp_anomaly_count": timestamp_anomaly_count,
        "symbol_coverage_count": symbol_coverage_count,
        "timeframe_coverage_count": timeframe_coverage_count,
        "quality_score": round(quality_score, 1),
        "quality_grade": quality_grade,
        "sample_quality_ready": sample_quality_ready,
        "audit_warnings": audit_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_sample_quality_audit.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Sample Quality Audit",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- samples_analyzed: {report['samples_analyzed']}",
        f"- unique_sample_keys: {report['unique_sample_keys']}",
        f"- duplicate_samples: {report['duplicate_samples']}",
        f"- missing_required_fields_count: {report['missing_required_fields_count']}",
        f"- timestamp_anomaly_count: {report['timestamp_anomaly_count']}",
        f"- symbol_coverage_count: {report['symbol_coverage_count']}",
        f"- timeframe_coverage_count: {report['timeframe_coverage_count']}",
        f"- quality_score: {report['quality_score']}",
        f"- quality_grade: {report['quality_grade']}",
        f"- sample_quality_ready: {report['sample_quality_ready']}",
        f"- audit_warnings: {report['audit_warnings']}",
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
    parser = argparse.ArgumentParser(description="Audit shadow sample quality")
    parser.add_argument("--shadow-sample-quality-json", default="reports/shadow_sample_quality/shadow_sample_quality_dashboard.json")
    parser.add_argument("--shadow-candidate-outcomes-json", default="reports/shadow_candidate_outcomes/summary.json")
    parser.add_argument("--output-dir", default="reports/shadow_sample_quality_audit")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = audit_shadow_sample_quality(
        shadow_sample_quality_json=str(args.shadow_sample_quality_json or "reports/shadow_sample_quality/shadow_sample_quality_dashboard.json"),
        shadow_candidate_outcomes_json=str(args.shadow_candidate_outcomes_json or "reports/shadow_candidate_outcomes/summary.json"),
        output_dir=str(args.output_dir or "reports/shadow_sample_quality_audit"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"sample_quality_ready={result.get('sample_quality_ready',False)}")


if __name__ == "__main__":
    main()
