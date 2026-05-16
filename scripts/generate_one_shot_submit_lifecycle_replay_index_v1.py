#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


INDEX_TYPE = "ONE_SHOT_SUBMIT_LIFECYCLE_REPLAY_INDEX_V1"
MAX_JSON_BYTES = 10 * 1024 * 1024
REQUIRED_PHASE_ORDER = [
    "SINGLE_MANUAL_SUBMIT_PACKET_GENERATION",
    "HUMAN_GATED_EXECUTION_WRAPPER_REVIEW",
    "SINGLE_HUMAN_GATED_EXECUTION_WRAPPER_ARTIFACT",
    "FINAL_HUMAN_GATED_ONE_SHOT_SUBMIT_REVIEW",
    "POST_HUMAN_SUBMIT_READONLY_VERIFICATION",
    "POST_HUMAN_SUBMIT_INCIDENT_REVIEW",
    "POST_HUMAN_SUBMIT_FINAL_CLOSEOUT",
]


def _has_unsafe_marker(data: Any) -> bool:
    if isinstance(data, str):
        lower = data.lower()
        return (
            "mainnet" in lower
            or "live" in lower
            or "api.binance.com" in lower
            or "fapi.binance.com" in lower
        )
    if isinstance(data, dict):
        return any(_has_unsafe_marker(v) for v in data.values())
    if isinstance(data, list):
        return any(_has_unsafe_marker(v) for v in data)
    return False


def _load_json_dict(path: str) -> Tuple[Optional[Dict[str, Any]], str]:
    if not path or not os.path.exists(path):
        return None, "MISSING_FILE"
    try:
        if os.path.getsize(path) > MAX_JSON_BYTES:
            return None, "FILE_TOO_LARGE"
    except Exception:
        return None, "STAT_ERROR"

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data, ""
        return None, "JSON_NOT_OBJECT"
    except Exception:
        return None, "INVALID_JSON"


def _phase_family_from_data_or_path(data: Dict[str, Any], path: str) -> str:
    candidates = [
        str(data.get("phase", "")),
        str(data.get("phase_family", "")),
        str(data.get("phase_name", "")),
        os.path.basename(path or ""),
    ]
    text = " ".join(candidates).upper()

    if "SINGLE_MANUAL_SUBMIT_PACKET_GENERATION" in text:
        return "SINGLE_MANUAL_SUBMIT_PACKET_GENERATION"
    if "HUMAN_GATED_EXECUTION_WRAPPER_REVIEW" in text:
        return "HUMAN_GATED_EXECUTION_WRAPPER_REVIEW"
    if "SINGLE_HUMAN_GATED_EXECUTION_WRAPPER_ARTIFACT" in text:
        return "SINGLE_HUMAN_GATED_EXECUTION_WRAPPER_ARTIFACT"
    if "FINAL_HUMAN_GATED_ONE_SHOT_SUBMIT_REVIEW" in text:
        return "FINAL_HUMAN_GATED_ONE_SHOT_SUBMIT_REVIEW"
    if "POST_HUMAN_SUBMIT_READONLY_VERIFICATION" in text:
        return "POST_HUMAN_SUBMIT_READONLY_VERIFICATION"
    if "POST_HUMAN_SUBMIT_INCIDENT_REVIEW" in text:
        return "POST_HUMAN_SUBMIT_INCIDENT_REVIEW"
    if "POST_HUMAN_SUBMIT_FINAL_CLOSEOUT" in text:
        return "POST_HUMAN_SUBMIT_FINAL_CLOSEOUT"
    return "UNKNOWN"


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def generate_replay_index(artifact_json_paths: List[str]) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    artifacts: List[Dict[str, Any]] = []
    phase_to_entries: Dict[str, List[Dict[str, Any]]] = {}

    for idx, path in enumerate(artifact_json_paths):
        data, load_error = _load_json_dict(path)
        parse_ok = data is not None
        phase_family = _phase_family_from_data_or_path(data or {}, path)

        artifact_entry = {
            "path": path,
            "parse_ok": parse_ok,
            "phase_family": phase_family,
            "readonly_marker": bool((data or {}).get("readonly")) if isinstance(data, dict) and "readonly" in data else None,
            "verdict": str((data or {}).get("verdict", "")),
            "decision": str((data or {}).get("decision", "")),
            "max_submit_count": int((data or {}).get("max_submit_count", 0)) if isinstance(data, dict) else 0,
            "load_error": load_error,
            "index": idx,
        }
        artifacts.append(artifact_entry)

        if not parse_ok:
            blockers.append(f"INVALID_OR_UNREADABLE_JSON:{path}:{load_error}")
            continue

        if phase_family == "UNKNOWN":
            warnings.append(f"UNKNOWN_PHASE_FAMILY:{path}")

        phase_to_entries.setdefault(phase_family, []).append(artifact_entry)

        if _has_unsafe_marker(data):
            blockers.append(f"UNSAFE_MARKER_DETECTED:{phase_family}:{path}")

        if bool(data.get("submit_allowed")):
            blockers.append(f"SUBMIT_ALLOWED_TRUE:{phase_family}:{path}")
        if bool(data.get("cancel_allowed")):
            blockers.append(f"CANCEL_ALLOWED_TRUE:{phase_family}:{path}")
        if bool(data.get("flatten_allowed")):
            blockers.append(f"FLATTEN_ALLOWED_TRUE:{phase_family}:{path}")

        if "readonly" not in data:
            warnings.append(f"OPTIONAL_METADATA_MISSING_READONLY:{phase_family}:{path}")
        elif bool(data.get("readonly")) is not True:
            blockers.append(f"READONLY_NOT_TRUE:{phase_family}:{path}")

        if "verdict" not in data:
            warnings.append(f"OPTIONAL_METADATA_MISSING_VERDICT:{phase_family}:{path}")

    missing_phases = [p for p in REQUIRED_PHASE_ORDER if len(phase_to_entries.get(p, [])) == 0]
    duplicated_phases = sorted([p for p, entries in phase_to_entries.items() if len(entries) > 1 and p != "UNKNOWN"])

    conflicting_duplicates: List[str] = []
    for phase in duplicated_phases:
        entries = phase_to_entries.get(phase, [])
        signatures = {
            (
                e.get("verdict", ""),
                e.get("decision", ""),
                e.get("readonly_marker", None),
                int(e.get("max_submit_count", 0)),
            )
            for e in entries
        }
        if len(signatures) > 1:
            conflicting_duplicates.append(phase)

    for phase in missing_phases:
        blockers.append(f"MISSING_REQUIRED_PHASE:{phase}")
    for phase in conflicting_duplicates:
        blockers.append(f"DUPLICATED_CONFLICTING_PHASE:{phase}")

    phase_order = [
        art["phase_family"]
        for art in sorted(artifacts, key=lambda x: x.get("index", 0))
        if art["phase_family"] in REQUIRED_PHASE_ORDER
    ]

    first_index: Dict[str, int] = {}
    for i, phase in enumerate(phase_order):
        if phase not in first_index:
            first_index[phase] = i

    ordered = True
    present_required = [p for p in REQUIRED_PHASE_ORDER if p in first_index]
    for i in range(1, len(present_required)):
        if first_index[present_required[i - 1]] > first_index[present_required[i]]:
            ordered = False
            break
    if present_required and not ordered:
        blockers.append("PHASE_ORDER_INVALID")

    all_required_exact_once = all(len(phase_to_entries.get(p, [])) == 1 for p in REQUIRED_PHASE_ORDER)

    if blockers:
        verdict = "FAIL"
        ok = False
    elif all_required_exact_once and ordered and not warnings:
        verdict = "PASS"
        ok = True
    else:
        verdict = "PARTIAL"
        ok = False

    return {
        "ok": ok,
        "verdict": verdict,
        "index_type": INDEX_TYPE,
        "artifact_count": len(artifacts),
        "phase_order": phase_order,
        "artifacts": artifacts,
        "missing_phases": missing_phases,
        "duplicated_phases": duplicated_phases,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate one-shot submit lifecycle replay index")
    parser.add_argument("--artifact-jsons", nargs="+", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_replay_index(args.artifact_jsons)

    if args.output_json and not write_json(args.output_json, report):
        print("failed_to_write_output", file=sys.stderr)
        return 1
    if args.json:
        if args.pretty:
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
