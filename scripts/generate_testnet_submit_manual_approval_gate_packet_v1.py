#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

PHASE = "testnet_submit_manual_approval_gate"
FORBIDDEN_ACTIONS = [
    "EXCHANGE_API_CALL",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]


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
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _has_readiness_signal(artifact: Dict[str, Any]) -> bool:
    final_decision = str(artifact.get("final_decision", ""))
    recommendation = str(artifact.get("recommendation", ""))
    recommendation_status = str(artifact.get("recommendation_status", ""))
    verdict = str(artifact.get("verdict", ""))
    return (
        final_decision == "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW"
        or recommendation == "PROCEED_TO_TESTNET_SUBMIT_READINESS_REVIEW"
        or recommendation_status == "DRY_RUN_TO_TESTNET_SUBMIT_READINESS_RECOMMENDED"
        or verdict == "PASS"
    )


def generate_gate_packet(input_paths: List[str]) -> Dict[str, Any]:
    reviewed_artifacts: List[Dict[str, Any]] = []
    blocking_reasons: List[str] = []
    warnings: List[str] = ["SUBMIT_NOT_EXECUTED"]

    readiness_signal = False

    for path in input_paths:
        payload = load_json(path)
        if payload is None:
            reviewed_artifacts.append({"path": path, "loaded": False})
            blocking_reasons.append(f"ARTIFACT_LOAD_FAILED:{path}")
            continue

        artifact_ok = payload.get("ok")
        artifact_blockers = payload.get("blockers")
        if artifact_ok is False:
            blocking_reasons.append(f"ARTIFACT_NOT_OK:{path}")
        if isinstance(artifact_blockers, list) and artifact_blockers:
            blocking_reasons.append(f"ARTIFACT_BLOCKERS_PRESENT:{path}")

        if _has_readiness_signal(payload):
            readiness_signal = True

        reviewed_artifacts.append(
            {
                "path": path,
                "loaded": True,
                "ok": bool(artifact_ok is True),
                "final_decision": payload.get("final_decision"),
                "verdict": payload.get("verdict"),
                "phase": payload.get("phase"),
            }
        )

    if not readiness_signal:
        blocking_reasons.append("PRIOR_READINESS_RECOMMENDATION_NOT_PASS")

    blocking_reasons = sorted(set(blocking_reasons))

    if readiness_signal and not blocking_reasons:
        verdict = "PASS"
        ok = True
    elif readiness_signal:
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "FAIL"
        ok = False

    required_manual_approvals = [
        "RISK_OWNER_APPROVAL",
        "STRATEGY_OWNER_APPROVAL",
        "OPS_OWNER_APPROVAL",
    ]

    next_allowed_actions = [
        "REVIEW_ONLY",
        "VERIFY_PAYLOAD_INVARIANTS_OFFLINE",
        "GENERATE_GO_NO_GO_CHECKLIST",
    ]

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "reviewed_artifacts": reviewed_artifacts,
        "required_manual_approvals": required_manual_approvals,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "next_allowed_actions": next_allowed_actions,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "submit_executed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate testnet submit manual approval gate packet")
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_gate_packet(args.inputs)
    if not write_json(args.output, report):
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
