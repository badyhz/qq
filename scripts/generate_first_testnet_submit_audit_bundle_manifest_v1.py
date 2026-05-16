#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
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


def sha256_file(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 64)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def infer_artifact_type(path: str, payload: Optional[Dict[str, Any]]) -> str:
    lower = path.lower()
    if "manual" in lower:
        return "manual_approval_packet"
    if "command" in lower:
        return "single_command_packet"
    if "confirmation" in lower or "token" in lower:
        return "confirmation_gate"
    if "execution" in lower or "wrapper" in lower:
        return "execution_wrapper_result"
    if "verification" in lower:
        return "post_submit_verification"
    if "evidence" in lower:
        return "submit_evidence"
    if "incident" in lower:
        return "incident_report"
    if "rollback" in lower:
        return "rollback_recommendation"
    if isinstance(payload, dict):
        if "incident_level" in payload:
            return "incident_report"
        if "recommendation" in payload:
            return "rollback_recommendation"
        if "submit_executed" in payload and "request_plan" in payload:
            return "execution_wrapper_result"
    return "unknown"


def _extract_env_symbol_submit(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"env": None, "symbol": None, "submit_executed": None}
    env = payload.get("env")
    symbol = payload.get("symbol")
    submit_executed = payload.get("submit_executed")

    if env is None and isinstance(payload.get("request_plan"), dict):
        env = payload["request_plan"].get("env")
    if symbol is None and isinstance(payload.get("request_plan"), dict):
        symbol = payload["request_plan"].get("symbol")
    if submit_executed is None and isinstance(payload.get("submit_result_summary"), dict):
        submit_executed = payload["submit_result_summary"].get("submit_executed")

    return {"env": env, "symbol": symbol, "submit_executed": submit_executed}


def generate_manifest(paths: Dict[str, str]) -> Dict[str, Any]:
    artifacts: List[Dict[str, Any]] = []
    missing_artifacts: List[str] = []
    invalid_artifacts: List[str] = []
    blockers: List[str] = []
    warnings: List[str] = []

    env_values = []
    symbol_values = []
    submit_exec_values = []
    optional_missing_fields = 0

    for name, path in sorted(paths.items()):
        exists = os.path.exists(path)
        size_bytes = os.path.getsize(path) if exists else 0
        digest = sha256_file(path) if exists else None
        payload = load_json(path) if exists else None
        json_load_ok = payload is not None
        artifact_type = infer_artifact_type(path, payload)

        if not exists:
            missing_artifacts.append(name)
        elif not json_load_ok:
            invalid_artifacts.append(name)

        extracted = _extract_env_symbol_submit(payload)
        if extracted["env"] is None:
            optional_missing_fields += 1
        else:
            env_values.append(str(extracted["env"]))
        if extracted["symbol"] is None:
            optional_missing_fields += 1
        else:
            symbol_values.append(str(extracted["symbol"]))
        if extracted["submit_executed"] is None:
            optional_missing_fields += 1
        else:
            submit_exec_values.append(bool(extracted["submit_executed"]))

        artifacts.append(
            {
                "name": name,
                "path": path,
                "exists": exists,
                "size_bytes": size_bytes,
                "sha256": digest,
                "json_load_ok": json_load_ok,
                "artifact_type": artifact_type,
            }
        )

    env_consistent = len(set(env_values)) <= 1 if env_values else True
    symbol_consistent = len(set(symbol_values)) <= 1 if symbol_values else True
    submit_consistent = len(set(submit_exec_values)) <= 1 if submit_exec_values else True

    if missing_artifacts:
        blockers.append("REQUIRED_ARTIFACT_MISSING")
    if invalid_artifacts:
        blockers.append("INVALID_JSON_ARTIFACT")
    if not env_consistent:
        blockers.append("CHAIN_ENV_MISMATCH")
    if not symbol_consistent:
        blockers.append("CHAIN_SYMBOL_MISMATCH")
    if not submit_consistent:
        blockers.append("CHAIN_SUBMIT_EXECUTED_MISMATCH")

    if optional_missing_fields > 0:
        warnings.append("OPTIONAL_CONSISTENCY_FIELDS_MISSING")

    chain_summary = {
        "env_values": sorted(set(env_values)),
        "symbol_values": sorted(set(symbol_values)),
        "submit_executed_values": sorted(set(submit_exec_values)),
        "env_consistent": env_consistent,
        "symbol_consistent": symbol_consistent,
        "submit_executed_consistent": submit_consistent,
        "optional_missing_fields": optional_missing_fields,
    }

    if blockers:
        verdict = "FAIL"
        ok = False
    elif warnings:
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    bundle_seed = json.dumps([[k, paths[k]] for k in sorted(paths.keys())], sort_keys=True, ensure_ascii=False)
    bundle_id = "bundle_" + hashlib.sha256(bundle_seed.encode("utf-8")).hexdigest()[:12]

    return {
        "ok": ok,
        "verdict": verdict,
        "bundle_id": bundle_id,
        "created_at": "1970-01-01T00:00:00Z",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "missing_artifacts": sorted(missing_artifacts),
        "invalid_artifacts": sorted(invalid_artifacts),
        "chain_summary": chain_summary,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate first testnet submit audit bundle manifest")
    parser.add_argument("--manual-approval-packet-json", required=True)
    parser.add_argument("--single-command-packet-json", required=True)
    parser.add_argument("--confirmation-gate-json", required=True)
    parser.add_argument("--execution-wrapper-result-json", required=True)
    parser.add_argument("--post-submit-verification-json", required=True)
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--incident-json", required=True)
    parser.add_argument("--rollback-recommendation-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_manifest(
        {
            "manual_approval_packet": args.manual_approval_packet_json,
            "single_command_packet": args.single_command_packet_json,
            "confirmation_gate": args.confirmation_gate_json,
            "execution_wrapper_result": args.execution_wrapper_result_json,
            "post_submit_verification": args.post_submit_verification_json,
            "evidence": args.evidence_json,
            "incident": args.incident_json,
            "rollback_recommendation": args.rollback_recommendation_json,
        }
    )

    if args.output_json:
        if not write_json(args.output_json, report):
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
