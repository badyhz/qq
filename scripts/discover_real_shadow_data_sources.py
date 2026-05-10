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


def discover_real_shadow_data_sources(
    reports_dir: str = "reports",
    data_dir: str = "data",
    logs_dir: str = "logs",
) -> dict[str, Any]:
    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    sources_scanned = 0
    eligible_source_count = 0
    excluded_source_count = 0
    eligible_sources: list[dict[str, Any]] = []
    excluded_sources: list[dict[str, Any]] = []
    missing_inputs: list[str] = []

    # Check observation_sample_store (MARKET_OBSERVATION)
    obs_store_path = Path(reports_dir) / "observation_sample_store"
    if obs_store_path.exists():
        sources_scanned += 1
        obs_csv = obs_store_path / "observation_samples.csv"
        obs_summary = obs_store_path / "summary.json"
        if obs_csv.exists() or obs_summary.exists():
            summary_data = _read_json(obs_summary)
            obs_count = summary_data.get("observation_count", 0)
            eligible_sources.append({
                "source_id": "observation_sample_store",
                "source_type": "MARKET_OBSERVATION",
                "path": str(obs_store_path),
                "record_estimate": obs_count,
                "reason": "Real market observation samples from shadow scanning"
            })
            eligible_source_count += 1
        else:
            excluded_sources.append({
                "path": str(obs_store_path),
                "reason": "No valid observation files found"
            })
            excluded_source_count += 1
    else:
        excluded_sources.append({
            "path": str(obs_store_path),
            "reason": "Directory does not exist"
        })
        excluded_source_count += 1

    # Check shadow_candidate_outcomes (OUTCOME_RECORD)
    candidate_outcomes_path = Path(reports_dir) / "shadow_candidate_outcomes"
    if candidate_outcomes_path.exists():
        sources_scanned += 1
        outcomes_csv = candidate_outcomes_path / "shadow_candidate_outcomes.csv"
        outcomes_summary = candidate_outcomes_path / "summary.json"
        if outcomes_csv.exists() or outcomes_summary.exists():
            eligible_sources.append({
                "source_id": "shadow_candidate_outcomes",
                "source_type": "OUTCOME_RECORD",
                "path": str(candidate_outcomes_path),
                "record_estimate": 0,  # Can read from CSV later if needed
                "reason": "Shadow candidate outcome records"
            })
            eligible_source_count += 1
        else:
            excluded_sources.append({
                "path": str(candidate_outcomes_path),
                "reason": "No valid outcome files found"
            })
            excluded_source_count += 1
    else:
        excluded_sources.append({
            "path": str(candidate_outcomes_path),
            "reason": "Directory does not exist"
        })
        excluded_source_count += 1

    # Check shadow_experiment_outcomes (OUTCOME_RECORD)
    exp_outcomes_path = Path(reports_dir) / "shadow_experiment_outcomes"
    if exp_outcomes_path.exists():
        sources_scanned += 1
        exp_outcomes_csv = exp_outcomes_path / "experiment_outcomes.csv"
        if exp_outcomes_csv.exists():
            eligible_sources.append({
                "source_id": "shadow_experiment_outcomes",
                "source_type": "OUTCOME_RECORD",
                "path": str(exp_outcomes_path),
                "record_estimate": 0,
                "reason": "Shadow experiment outcome records"
            })
            eligible_source_count += 1
        else:
            excluded_sources.append({
                "path": str(exp_outcomes_path),
                "reason": "No valid experiment outcome files found"
            })
            excluded_source_count += 1
    else:
        excluded_sources.append({
            "path": str(exp_outcomes_path),
            "reason": "Directory does not exist"
        })
        excluded_source_count += 1

    # Check shadow_remediation_history (SHADOW_LOG)
    shadow_history_path = Path(data_dir) / "shadow_remediation_history"
    if shadow_history_path.exists():
        sources_scanned += 1
        history_json = shadow_history_path / "history.json"
        if history_json.exists():
            eligible_sources.append({
                "source_id": "shadow_remediation_history",
                "source_type": "SHADOW_LOG",
                "path": str(shadow_history_path),
                "record_estimate": 0,
                "reason": "Shadow remediation history logs"
            })
            eligible_source_count += 1
        else:
            excluded_sources.append({
                "path": str(shadow_history_path),
                "reason": "No valid history file found"
            })
            excluded_source_count += 1
    else:
        excluded_sources.append({
            "path": str(shadow_history_path),
            "reason": "Directory does not exist"
        })
        excluded_source_count += 1

    discovery_ready = eligible_source_count > 0

    final_verdict = "PASS"
    if eligible_source_count == 0:
        final_verdict = "PARTIAL"
        missing_inputs.append("no_eligible_shadow_data_sources_found")

    # Safety checks
    safety_ok = True
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        safety_ok = False
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"
        safety_ok = False

    report: dict[str, Any] = {
        "task_id": "T391",
        "phase": "REAL_SHADOW_DATA_SOURCE_DISCOVERY",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "sources_scanned": sources_scanned,
        "eligible_source_count": eligible_source_count,
        "excluded_source_count": excluded_source_count,
        "eligible_sources": eligible_sources,
        "excluded_sources": excluded_sources,
        "discovery_ready": discovery_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover real shadow data sources")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = discover_real_shadow_data_sources(
        reports_dir=args.reports_dir,
        data_dir=args.data_dir,
        logs_dir=args.logs_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"eligible_source_count={result.get('eligible_source_count',0)}")
    print(f"discovery_ready={result.get('discovery_ready',False)}")


if __name__ == "__main__":
    main()
