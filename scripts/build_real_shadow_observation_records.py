from __future__ import annotations

import argparse
import csv
import json
import uuid
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


def build_real_shadow_observation_records(
    discovery_result: dict[str, Any] | None = None,
    reports_dir: str = "reports",
    output_dir: str = "reports/real_shadow_observation_build",
) -> dict[str, Any]:
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

    source_discovery_ready = False
    eligible_source_count = 0
    records_built = 0
    records: list[dict[str, Any]] = []
    missing_required_field_records = 0
    placeholder_records_rejected = 0
    missing_inputs: list[str] = []

    if discovery_result is None:
        # Try to read from default location
        discovery_path = Path(reports_dir) / "real_shadow_data_source_discovery" / "real_shadow_data_source_discovery.json"
        if discovery_path.exists():
            discovery_result = _read_json(discovery_path)
        else:
            missing_inputs.append("discovery_result_not_provided_and_not_found")

    if discovery_result:
        source_discovery_ready = discovery_result.get("discovery_ready", False)
        eligible_source_count = discovery_result.get("eligible_source_count", 0)
        eligible_sources = discovery_result.get("eligible_sources", [])

        # Process observation_sample_store (MARKET_OBSERVATION)
        for source in eligible_sources:
            source_id = source.get("source_id", "")
            source_type = source.get("source_type", "")
            source_path = source.get("path", "")

            if source_id == "observation_sample_store" and source_type == "MARKET_OBSERVATION":
                obs_csv_path = Path(source_path) / "observation_samples.csv"
                if obs_csv_path.exists():
                    try:
                        with open(obs_csv_path, newline="", encoding="utf-8") as csvfile:
                            reader = csv.DictReader(csvfile)
                            for row_idx, row in enumerate(reader):
                                symbol = row.get("symbol", "")
                                timeframe = row.get("timeframe", "")
                                setup = row.get("strategy_key", "observation")
                                timestamp = row.get("created_at", datetime.now(timezone.utc).isoformat())

                                if not symbol or not timeframe:
                                    missing_required_field_records += 1
                                    continue

                                record_id = f"REAL_OBS_{uuid.uuid4().hex[:8]}"
                                record = {
                                    "record_id": record_id,
                                    "source_id": source_id,
                                    "source_type": source_type,
                                    "symbol": symbol,
                                    "timeframe": timeframe,
                                    "setup": setup,
                                    "timestamp": timestamp,
                                    "observation_only": True,
                                    "synthetic_placeholder": False,
                                    "status": "COLLECTED",
                                    "reason": "Real market observation from observation_sample_store",
                                }
                                records.append(record)
                                records_built += 1
                    except (OSError, csv.Error):
                        pass

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if records_built == 0 and eligible_source_count > 0:
        final_verdict = "PARTIAL"

    # Safety checks
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T392",
        "phase": "REAL_SHADOW_OBSERVATION_RECORD_BUILD",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "source_discovery_ready": source_discovery_ready,
        "eligible_source_count": eligible_source_count,
        "records_built": records_built,
        "records": records,
        "missing_required_field_records": missing_required_field_records,
        "placeholder_records_rejected": placeholder_records_rejected,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "real_shadow_observation_build.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build real shadow observation records")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--output-dir", default="reports/real_shadow_observation_build")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = build_real_shadow_observation_records(
        reports_dir=args.reports_dir,
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"records_built={result.get('records_built',0)}")


if __name__ == "__main__":
    main()
