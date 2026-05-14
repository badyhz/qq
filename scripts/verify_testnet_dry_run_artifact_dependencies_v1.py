#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_DRY_RUN_ONLY",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

REQUIRED_INPUT_ARTIFACTS = [f"T{i}" for i in range(426, 441)]
REQUIRED_OUTPUT_ARTIFACTS = [f"T{i}" for i in range(441, 446)]

SAFETY_FLAGS = {
    "shadow_only": True,
    "testnet_dry_run_allowed": False,
    "testnet_submit_allowed": False,
    "real_submit_allowed": False,
    "submit_attempted": False,
    "cancel_attempted": False,
    "flatten_attempted": False,
}

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "VERIFY_TESTNET_DRY_RUN_ARTIFACT_DEPENDENCIES",
    "MANUAL_REVIEW_ONLY",
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        return True
    except Exception:
        return False


def verify_artifact_dependencies(
    readiness_input_packet: Optional[Dict[str, Any]],
    safety_constraint_report: Optional[Dict[str, Any]],
    artifact_manifest: Optional[Dict[str, Any]],
    readiness_input_path: str,
    safety_constraint_path: str,
    artifact_manifest_path: str,
) -> Dict[str, Any]:
    missing_dependencies: List[str] = []

    t441_ok = (
        readiness_input_packet
        and readiness_input_packet.get("ok") is True
        and readiness_input_packet.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINT_REVIEW"
    )
    if not t441_ok:
        missing_dependencies.append("READINESS_INPUT_PACKET_NOT_READY")

    t442_ok = (
        safety_constraint_report
        and safety_constraint_report.get("ok") is True
        and safety_constraint_report.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_ARTIFACT_DEPENDENCY_REVIEW"
    )
    if not t442_ok:
        missing_dependencies.append("SAFETY_CONSTRAINTS_NOT_VERIFIED")

    manifest_inputs = []
    manifest_outputs = []
    operator_review_required = False
    manual_approval_required = False

    if artifact_manifest:
        manifest_inputs = artifact_manifest.get("input_artifacts") or []
        manifest_outputs = artifact_manifest.get("output_artifacts") or []
        operator_review_required = artifact_manifest.get("operator_review_required") is True
        manual_approval_required = artifact_manifest.get("manual_approval_required") is True

    for artifact in REQUIRED_INPUT_ARTIFACTS:
        if artifact not in manifest_inputs:
            missing_dependencies.append(f"INPUT_ARTIFACT_{artifact}_MISSING")

    for artifact in REQUIRED_OUTPUT_ARTIFACTS:
        if artifact not in manifest_outputs:
            missing_dependencies.append(f"OUTPUT_ARTIFACT_{artifact}_MISSING")

    if not operator_review_required:
        missing_dependencies.append("OPERATOR_REVIEW_NOT_REQUIRED")

    if not manual_approval_required:
        missing_dependencies.append("MANUAL_APPROVAL_NOT_REQUIRED")

    ok = len(missing_dependencies) == 0

    if ok:
        dependency_status = "TESTNET_DRY_RUN_ARTIFACT_DEPENDENCIES_VERIFIED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_READINESS_SCORE"
    else:
        dependency_status = "ARTIFACT_DEPENDENCY_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_READINESS_REVIEW"

    return {
        "ok": ok,
        "task": "T443",
        "phase": "TESTNET_DRY_RUN_READINESS_REVIEW",
        "source_reports": {
            "readiness_input_packet": readiness_input_path,
            "safety_constraint_report": safety_constraint_path,
            "artifact_manifest": artifact_manifest_path,
        },
        "dependency_status": dependency_status,
        "dependency_summary": {
            "required_input_artifact_count": len(REQUIRED_INPUT_ARTIFACTS),
            "required_output_artifact_count": len(REQUIRED_OUTPUT_ARTIFACTS),
            "provided_input_artifact_count": len(manifest_inputs),
            "provided_output_artifact_count": len(manifest_outputs),
            "operator_review_required": operator_review_required,
            "manual_approval_required": manual_approval_required,
        },
        "missing_dependencies": missing_dependencies,
        "safety_flags": dict(SAFETY_FLAGS),
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Verify TESTNET_DRY_RUN_READINESS_REVIEW artifact dependencies"
    )
    parser.add_argument(
        "--readiness-input-packet",
        type=str,
        required=True,
        help="Path to T441 readiness input packet JSON",
    )
    parser.add_argument(
        "--safety-constraint-report",
        type=str,
        required=True,
        help="Path to T442 safety constraint report JSON",
    )
    parser.add_argument(
        "--artifact-manifest",
        type=str,
        required=True,
        help="Path to artifact manifest JSON",
    )
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    readiness_input_packet = load_json(args.readiness_input_packet)
    safety_constraint_report = load_json(args.safety_constraint_report)
    artifact_manifest = load_json(args.artifact_manifest)

    report = verify_artifact_dependencies(
        readiness_input_packet,
        safety_constraint_report,
        artifact_manifest,
        args.readiness_input_packet,
        args.safety_constraint_report,
        args.artifact_manifest,
    )

    if args.output:
        write_ok = write_json(args.output, report)
        if not write_ok:
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
