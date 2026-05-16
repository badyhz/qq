#!/usr/bin/env python3
import argparse
import datetime
import hashlib
import json
import os
import sys
import uuid
from typing import Any, Dict, Optional, List


def sha256_file(path: str) -> Optional[str]:
    if not path or not os.path.exists(path):
        return None
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            # Read in chunks to handle large files safely
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def load_json_safe(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return None
    try:
        # Read only up to 1MB to avoid loading huge files
        if os.path.getsize(path) > 1048576:
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _has_live_marker(data: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(data, dict):
        return False
    for k, v in data.items():
        if isinstance(v, str):
            lower = v.lower()
            if "mainnet" in lower or "live" in lower or "api.binance.com" in lower:
                return True
        elif isinstance(v, dict):
            if _has_live_marker(v):
                return True
    return False


def generate_manifest(
    wrapper_phase_path: Optional[str],
    final_safety_gate_path: Optional[str],
    wrapper_artifact_path: Optional[str],
    wrapper_invariant_path: Optional[str],
    command_preview_path: Optional[str],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    artifact_paths = {
        "wrapper_phase": wrapper_phase_path,
        "final_safety_gate": final_safety_gate_path,
        "wrapper_artifact": wrapper_artifact_path,
        "wrapper_invariant": wrapper_invariant_path,
        "command_preview": command_preview_path,
    }

    artifacts = []
    missing_artifacts = []
    invalid_artifacts = []
    loaded = {}

    for name, path in artifact_paths.items():
        exists = path and os.path.exists(path)
        size_bytes = os.path.getsize(path) if exists else 0
        sha256_hash = sha256_file(path) if exists else None
        json_data = load_json_safe(path) if exists else None
        json_load_ok = json_data is not None
        artifact_type = str((json_data or {}).get("artifact_type", "") or (json_data or {}).get("invariant_status", "") or (json_data or {}).get("command_preview_type", "") or "UNKNOWN")

        art = {
            "path": path or "",
            "exists": exists,
            "size_bytes": size_bytes,
            "sha256": sha256_hash,
            "json_load_ok": json_load_ok,
            "artifact_type": artifact_type,
        }
        artifacts.append(art)
        loaded[name] = json_data

        if not exists:
            missing_artifacts.append(name)
            blockers.append(f"{name.upper()}_MISSING")
        elif not json_load_ok:
            invalid_artifacts.append(name)
            blockers.append(f"{name.upper()}_INVALID_JSON")

    # Chain consistency checks
    all_json_ok = all(v is not None for v in loaded.values())
    env_consistent = True
    max_submit_count_ok = True
    submit_allowed_false = True
    no_live_marker = True

    if all_json_ok:
        envs = set()
        for name, data in loaded.items():
            env_val = str(data.get("env", "")).strip().lower()
            if env_val:
                envs.add(env_val)
            if _has_live_marker(data):
                no_live_marker = False
                blockers.append(f"{name.upper()}_HAS_LIVE_MARKER")
            if bool(data.get("submit_allowed") is True):
                submit_allowed_false = False
                blockers.append(f"{name.upper()}_SUBMIT_ALLOWED_TRUE")
            if int(data.get("max_submit_count", 1)) > 1:
                max_submit_count_ok = False
                blockers.append(f"{name.upper()}_MAX_SUBMIT_COUNT_GT_1")

        if len(envs) > 1:
            env_consistent = False
            blockers.append("ENV_MISMATCH_ACROSS_ARTIFACTS")
        if "testnet" not in envs and envs:
            env_consistent = False
            blockers.append("ENV_NOT_TESTNET")

    # Optional fields check
    has_summary = True  # We'll always generate it

    if blockers:
        verdict = "FAIL"
        ok = False
    elif warnings:
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "manifest_type": "SINGLE_HUMAN_GATED_EXECUTION_AUDIT",
        "bundle_id": str(uuid.uuid4()),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "chain_summary": {
            "env_consistent": env_consistent,
            "max_submit_count_ok": max_submit_count_ok,
            "submit_allowed_false": submit_allowed_false,
            "no_live_marker": no_live_marker,
        },
        "missing_artifacts": missing_artifacts,
        "invalid_artifacts": invalid_artifacts,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single human-gated execution local audit manifest")
    parser.add_argument("--wrapper-phase-json", required=True)
    parser.add_argument("--final-safety-gate-json", required=True)
    parser.add_argument("--wrapper-artifact-json", required=True)
    parser.add_argument("--wrapper-invariant-json", required=True)
    parser.add_argument("--command-preview-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_manifest(
        args.wrapper_phase_json,
        args.final_safety_gate_json,
        args.wrapper_artifact_json,
        args.wrapper_invariant_json,
        args.command_preview_json,
    )

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
