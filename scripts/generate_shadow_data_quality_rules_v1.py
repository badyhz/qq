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
    shadow_sample_quality_audit_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_sample_quality_audit_json).exists():
        missing.append("shadow_sample_quality_audit_json")
    return missing


def generate_shadow_data_quality_rules_v1(
    *,
    shadow_sample_quality_audit_json: str = "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json",
    output_dir: str = "reports/shadow_data_quality_rules_v1",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_sample_quality_audit_json=shadow_sample_quality_audit_json,
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

    quality_audit = _read_json(Path(shadow_sample_quality_audit_json))

    rules_version = "v1"
    rule_count = 0
    quality_gate_ready = False

    required_fields = [
        "timestamp",
        "symbol",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    dedupe_key_fields = [
        "timestamp",
        "symbol",
        "timeframe",
    ]

    timestamp_rules = {
        "required": True,
        "timezone": "UTC",
        "allow_future_timestamp": False,
    }

    coverage_rules = {
        "min_symbol_coverage": 2,
        "min_timeframe_coverage": 2,
        "min_samples_per_bucket": 5,
    }

    rule_count = 3 + len(required_fields) + len(dedupe_key_fields)
    quality_gate_ready = True

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    if timestamp_rules["allow_future_timestamp"]:
        final_verdict = "FAIL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T382",
        "phase": "SHADOW_DATA_QUALITY_RULES_V1",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "rules_version": rules_version,
        "rule_count": rule_count,
        "required_fields": required_fields,
        "dedupe_key_fields": dedupe_key_fields,
        "timestamp_rules": timestamp_rules,
        "coverage_rules": coverage_rules,
        "quality_gate_ready": quality_gate_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_data_quality_rules_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Data Quality Rules V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- rules_version: {report['rules_version']}",
        f"- rule_count: {report['rule_count']}",
        f"- required_fields count: {len(report['required_fields'])}",
        f"- dedupe_key_fields count: {len(report['dedupe_key_fields'])}",
        f"- quality_gate_ready: {report['quality_gate_ready']}",
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
    parser = argparse.ArgumentParser(description="Generate shadow data quality rules v1")
    parser.add_argument("--shadow-sample-quality-audit-json", default="reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json")
    parser.add_argument("--output-dir", default="reports/shadow_data_quality_rules_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_data_quality_rules_v1(
        shadow_sample_quality_audit_json=str(args.shadow_sample_quality_audit_json or "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json"),
        output_dir=str(args.output_dir or "reports/shadow_data_quality_rules_v1"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"quality_gate_ready={result.get('quality_gate_ready',False)}")


if __name__ == "__main__":
    main()
