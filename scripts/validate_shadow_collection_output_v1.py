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
    shadow_collection_round_v1_json: str,
    shadow_data_quality_rules_v1_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_collection_round_v1_json).exists():
        missing.append("shadow_collection_round_v1_json")
    if not Path(shadow_data_quality_rules_v1_json).exists():
        missing.append("shadow_data_quality_rules_v1_json")
    return missing


def validate_shadow_collection_output_v1(
    *,
    shadow_collection_round_v1_json: str = "reports/shadow_collection_round_v1/shadow_collection_round_v1.json",
    shadow_data_quality_rules_v1_json: str = "reports/shadow_data_quality_rules_v1/shadow_data_quality_rules_v1.json",
    output_dir: str = "reports/shadow_collection_output_validation_v1",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_collection_round_v1_json=shadow_collection_round_v1_json,
        shadow_data_quality_rules_v1_json=shadow_data_quality_rules_v1_json,
    )

    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    collection_round = _read_json(Path(shadow_collection_round_v1_json))
    rules = _read_json(Path(shadow_data_quality_rules_v1_json))

    records = collection_round.get("records", []) if isinstance(collection_round.get("records"), list) else []
    required_fields = rules.get("required_fields", []) if isinstance(rules.get("required_fields"), list) else []
    dedupe_keys = rules.get("dedupe_key_fields", []) if isinstance(rules.get("dedupe_key_fields"), list) else []

    records_analyzed = len(records)
    valid_records = 0
    invalid_records = 0
    duplicate_records = 0
    missing_required_fields_count = 0
    timestamp_anomaly_count = 0
    validation_warnings: list[str] = []
    valid_record_list: list[dict[str, Any]] = []
    gap_closure_eligible_records: list[dict[str, Any]] = []

    seen_dedupe_keys: set[tuple[str, ...]] = set()

    symbols: set[str] = set()
    timeframes: set[str] = set()
    setups: set[str] = set()

    for record in records:
        is_valid = True
        has_required_fields = True
        has_valid_timestamp = True
        is_duplicate = False

        for field in required_fields:
            if field not in record:
                has_required_fields = False

        timestamp = record.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if dt > datetime.now(timezone.utc):
                    has_valid_timestamp = False
            except ValueError:
                has_valid_timestamp = False

        dedupe_tuple = tuple(str(record.get(key, "")) for key in dedupe_keys)
        if dedupe_tuple in seen_dedupe_keys:
            is_duplicate = True
        else:
            seen_dedupe_keys.add(dedupe_tuple)

        if is_duplicate:
            duplicate_records += 1
            is_valid = False
        if not has_required_fields:
            missing_required_fields_count += 1
            is_valid = False
        if not has_valid_timestamp:
            timestamp_anomaly_count += 1
            is_valid = False

        if is_valid:
            valid_records += 1
            valid_record_list.append(record)
        else:
            invalid_records += 1

        symbols.add(record.get("symbol", ""))
        timeframes.add(record.get("timeframe", ""))
        setups.add(record.get("setup", ""))

    symbol_coverage_count = len([s for s in symbols if s])
    timeframe_coverage_count = len([t for t in timeframes if t])
    setup_coverage_count = len([s for s in setups if s])

    if duplicate_records > 0:
        validation_warnings.append(f"found {duplicate_records} duplicate records")

    if records_analyzed > 0:
        quality_score = max(0.0, min(100.0, (valid_records / records_analyzed) * 100.0))
    else:
        quality_score = 0.0

    quality_passed = valid_records > 0 and invalid_records == 0 and duplicate_records == 0

    # Data authenticity checks: only non-synthetic records from real sources are eligible
    authentic_source_types = {"SHADOW_LOG", "MARKET_OBSERVATION", "OUTCOME_RECORD"}
    data_authenticity_passed = False
    if quality_passed and len(valid_record_list) > 0:
        data_authenticity_passed = True
        for record in valid_record_list:
            synthetic = record.get("synthetic_placeholder", True)
            source_type = record.get("source_type", "QUEUE_PLACEHOLDER")
            if synthetic or source_type not in authentic_source_types:
                data_authenticity_passed = False
                break

    valid_for_gap_closure = data_authenticity_passed and quality_passed

    # Filter gap closure eligible records
    if valid_for_gap_closure:
        gap_closure_eligible_records = valid_record_list

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if records_analyzed == 0:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T387",
        "phase": "SHADOW_COLLECTION_OUTPUT_VALIDATION_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "records_analyzed": records_analyzed,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "duplicate_records": duplicate_records,
        "missing_required_fields_count": missing_required_fields_count,
        "timestamp_anomaly_count": timestamp_anomaly_count,
        "symbol_coverage_count": symbol_coverage_count,
        "timeframe_coverage_count": timeframe_coverage_count,
        "setup_coverage_count": setup_coverage_count,
        "quality_score": round(quality_score, 1),
        "quality_passed": quality_passed,
        "data_authenticity_passed": data_authenticity_passed,
        "valid_for_gap_closure": valid_for_gap_closure,
        "valid_record_list": valid_record_list,
        "gap_closure_eligible_records": gap_closure_eligible_records,
        "validation_warnings": validation_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_collection_output_validation_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Collection Output Validation V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- records_analyzed: {report['records_analyzed']}",
        f"- valid_records: {report['valid_records']}",
        f"- invalid_records: {report['invalid_records']}",
        f"- duplicate_records: {report['duplicate_records']}",
        f"- missing_required_fields_count: {report['missing_required_fields_count']}",
        f"- timestamp_anomaly_count: {report['timestamp_anomaly_count']}",
        f"- symbol_coverage_count: {report['symbol_coverage_count']}",
        f"- timeframe_coverage_count: {report['timeframe_coverage_count']}",
        f"- setup_coverage_count: {report['setup_coverage_count']}",
        f"- quality_score: {report['quality_score']}",
        f"- quality_passed: {report['quality_passed']}",
        f"- data_authenticity_passed: {report['data_authenticity_passed']}",
        f"- valid_for_gap_closure: {report['valid_for_gap_closure']}",
        f"- validation_warnings: {report['validation_warnings']}",
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
    parser = argparse.ArgumentParser(description="Validate shadow collection output v1")
    parser.add_argument("--shadow-collection-round-v1-json", default="reports/shadow_collection_round_v1/shadow_collection_round_v1.json")
    parser.add_argument("--shadow-data-quality-rules-v1-json", default="reports/shadow_data_quality_rules_v1/shadow_data_quality_rules_v1.json")
    parser.add_argument("--output-dir", default="reports/shadow_collection_output_validation_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = validate_shadow_collection_output_v1(
        shadow_collection_round_v1_json=str(args.shadow_collection_round_v1_json or "reports/shadow_collection_round_v1/shadow_collection_round_v1.json"),
        shadow_data_quality_rules_v1_json=str(args.shadow_data_quality_rules_v1_json or "reports/shadow_data_quality_rules_v1/shadow_data_quality_rules_v1.json"),
        output_dir=str(args.output_dir or "reports/shadow_collection_output_validation_v1"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"quality_passed={result.get('quality_passed',False)}")


if __name__ == "__main__":
    main()
