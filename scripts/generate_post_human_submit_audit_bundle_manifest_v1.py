#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
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


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _has_unsafe_marker(data: Any) -> bool:
    if isinstance(data, str):
        lower = data.lower()
        if "mainnet" in lower or "live" in lower or "api.binance.com" in lower or "fapi.binance.com" in lower:
            return True
    elif isinstance(data, dict):
        for k, v in data.items():
            if _has_unsafe_marker(v):
                return True
    elif isinstance(data, list):
        for item in data:
            if _has_unsafe_marker(item):
                return True
    return False


def _infer_artifact_type(path: str) -> str:
    basename = os.path.basename(path).lower()
    if "final_one_shot" in basename or "final-one-shot" in basename:
        return "FINAL_ONE_SHOT_PHASE"
    elif "verification_eligibility" in basename or "verification-eligibility" in basename:
        return "VERIFICATION_ELIGIBILITY"
    elif "receipt_parser" in basename or "receipt-parser" in basename:
        return "RECEIPT_PARSER"
    elif "protection_plan" in basename or "protection-plan" in basename:
        return "PROTECTION_PLAN"
    elif "readonly_evidence" in basename or "readonly-evidence" in basename:
        return "READONLY_EVIDENCE"
    elif "verification_phase" in basename or "verification-phase" in basename:
        return "VERIFICATION_PHASE"
    elif "incident" in basename:
        return "INCIDENT"
    elif "rollback_eligibility" in basename or "rollback-eligibility" in basename:
        return "ROLLBACK_ELIGIBILITY"
    elif "operator_checklist" in basename or "operator-checklist" in basename:
        return "OPERATOR_CHECKLIST"
    elif "incident_review_phase" in basename or "incident-review-phase" in basename:
        return "INCIDENT_REVIEW_PHASE"
    return "UNKNOWN"


def generate_manifest(
    final_one_shot_phase_path: Optional[str],
    verification_eligibility_path: Optional[str],
    receipt_parser_path: Optional[str],
    protection_plan_path: Optional[str],
    readonly_evidence_path: Optional[str],
    verification_phase_path: Optional[str],
    incident_path: Optional[str],
    rollback_eligibility_path: Optional[str],
    operator_checklist_path: Optional[str],
    incident_review_phase_path: Optional[str],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    required_artifacts = [
        ("final_one_shot_phase", final_one_shot_phase_path),
        ("verification_eligibility", verification_eligibility_path),
        ("receipt_parser", receipt_parser_path),
        ("protection_plan", protection_plan_path),
        ("readonly_evidence", readonly_evidence_path),
        ("verification_phase", verification_phase_path),
        ("incident", incident_path),
        ("rollback_eligibility", rollback_eligibility_path),
        ("operator_checklist", operator_checklist_path),
        ("incident_review_phase", incident_review_phase_path),
    ]

    artifacts = []
    missing_artifacts = []
    invalid_artifacts = []
    loaded_datas = {}

    for name, path in required_artifacts:
        if not path or not os.path.exists(path):
            missing_artifacts.append(name.upper())
            artifacts.append({
                "path": path or "",
                "exists": False,
                "size_bytes": 0,
                "sha256": "",
                "json_load_ok": False,
                "artifact_type": _infer_artifact_type(path or name),
            })
            continue

        size_bytes = os.path.getsize(path)
        sha256 = _sha256_file(path)
        data = load_json(path)
        json_load_ok = data is not None

        if not json_load_ok:
            invalid_artifacts.append(name.upper())

        artifacts.append({
            "path": path,
            "exists": True,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "json_load_ok": json_load_ok,
            "artifact_type": _infer_artifact_type(path),
        })

        if json_load_ok:
            loaded_datas[name] = data

    for name, data in loaded_datas.items():
        if _has_unsafe_marker(data):
            blockers.append(f"{name.upper()}_HAS_UNSAFE_MARKER")

        if bool(data.get("submit_allowed")) is True:
            blockers.append(f"{name.upper()}_SUBMIT_ALLOWED_TRUE")
        if bool(data.get("cancel_allowed")) is True:
            blockers.append(f"{name.upper()}_CANCEL_ALLOWED_TRUE")
        if bool(data.get("flatten_allowed")) is True:
            blockers.append(f"{name.upper()}_FLATTEN_ALLOWED_TRUE")

        if "verification" in name or "review" in name:
            if int(data.get("max_submit_count", 0)) != 0:
                blockers.append(f"{name.upper()}_MAX_SUBMIT_COUNT_NOT_ZERO")

        env = str(data.get("env", "")).strip().lower()
        if env and env != "testnet":
            blockers.append(f"{name.upper()}_ENV_NOT_TESTNET")

        readonly = bool(data.get("readonly"))
        if "readonly" in name and readonly is not True:
            blockers.append(f"{name.upper()}_READONLY_NOT_TRUE")

    chain_summary = {
        "total_artifacts": len(required_artifacts),
        "existing_artifacts": len([a for a in artifacts if a["exists"]]),
        "valid_json_artifacts": len([a for a in artifacts if a["json_load_ok"]]),
        "incident_level": str((loaded_datas.get("incident", {})).get("incident_level", "UNKNOWN")),
    }

    if missing_artifacts:
        for name in missing_artifacts:
            blockers.append(f"REQUIRED_{name}_MISSING")

    if blockers:
        verdict = "FAIL"
        ok = False
    elif invalid_artifacts:
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    bundle_id = f"post_human_submit_audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_UTC"

    return {
        "ok": ok,
        "verdict": verdict,
        "manifest_type": "POST_HUMAN_SUBMIT_AUDIT_BUNDLE",
        "bundle_id": bundle_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "chain_summary": chain_summary,
        "missing_artifacts": sorted(set(missing_artifacts)),
        "invalid_artifacts": sorted(set(invalid_artifacts)),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit audit bundle manifest")
    parser.add_argument("--final-one-shot-phase-json", required=True)
    parser.add_argument("--verification-eligibility-json", required=True)
    parser.add_argument("--receipt-parser-json", required=True)
    parser.add_argument("--protection-plan-json", required=True)
    parser.add_argument("--readonly-evidence-json", required=True)
    parser.add_argument("--verification-phase-json", required=True)
    parser.add_argument("--incident-json", required=True)
    parser.add_argument("--rollback-eligibility-json", required=True)
    parser.add_argument("--operator-checklist-json", required=True)
    parser.add_argument("--incident-review-phase-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    manifest = generate_manifest(
        args.final_one_shot_phase_json,
        args.verification_eligibility_json,
        args.receipt_parser_json,
        args.protection_plan_json,
        args.readonly_evidence_json,
        args.verification_phase_json,
        args.incident_json,
        args.rollback_eligibility_json,
        args.operator_checklist_json,
        args.incident_review_phase_json,
    )

    if args.output_json and not write_json(args.output_json, manifest):
        print("failed_to_write_output", file=sys.stderr)
        return 1
    if args.json:
        if args.pretty:
            print(json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(manifest, sort_keys=True, ensure_ascii=False))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
