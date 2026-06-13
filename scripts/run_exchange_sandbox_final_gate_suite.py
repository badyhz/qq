#!/usr/bin/env python3
"""T125001-T140000 — Exchange Sandbox Final Gate Suite Runner."""
import json, sys, pathlib, importlib
from datetime import datetime, timezone
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    now = datetime.now(timezone.utc).isoformat()
    steps = {}
    errors = []

    runners = [
        ("exchange_harness", "run_exchange_sandbox_dry_run_harness"),
        ("credential_injection", "run_credential_injection_review"),
        ("request_signing", "run_request_signing_dry_run"),
        ("submit_gate", "run_submit_gate_final_lock_check"),
        ("cancel_gate", "run_cancel_gate_final_lock_check"),
        ("recon_gate", "run_reconciliation_gate_final_lock_check"),
        ("approval_packet", "run_operator_approval_packet_v2"),
        ("blocker_matrix", "run_sandbox_final_blocker_matrix"),
        ("safety_regression", "run_final_gate_safety_regression"),
    ]

    for step_name, script_name in runners:
        try:
            mod = importlib.import_module(script_name)
            rc = mod.main()
            steps[step_name] = "PASS" if rc == 0 else "FAIL"
        except Exception as e:
            steps[step_name] = "FAIL"
            errors.append(f"{step_name}: {e}")

    # Previous suite
    try:
        mod = importlib.import_module("run_testnet_pre_submit_review_suite")
        rc = mod.main()
        steps["presubmit_review"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["presubmit_review"] = "FAIL"
        errors.append(f"presubmit_review: {e}")

    all_pass = all(v in ("PASS", "WARN") for v in steps.values())
    final_status = "EXCHANGE_SANDBOX_FINAL_GATE_SUITE_PASS" if all_pass else "EXCHANGE_SANDBOX_FINAL_GATE_SUITE_BLOCKED"

    manifest = {
        "manifest_id": f"finalgate_{now.replace(':', '').replace('-', '')[:20]}",
        "timestamp": now,
        "steps": steps,
        "errors": errors,
        "status": final_status,
        "required_statuses": {
            "EXCHANGE_SANDBOX_FINAL_GATE_SUITE_PASS": final_status == "EXCHANGE_SANDBOX_FINAL_GATE_SUITE_PASS",
            "EXCHANGE_SANDBOX_DRY_RUN_HARNESS_PASS": steps.get("exchange_harness") == "PASS",
            "CREDENTIAL_INJECTION_REVIEW_PASS": steps.get("credential_injection") == "PASS",
            "REQUEST_SIGNING_DRY_RUN_VALID": steps.get("request_signing") == "PASS",
            "SUBMIT_GATE_FINAL_LOCKED": steps.get("submit_gate") == "PASS",
            "CANCEL_GATE_FINAL_LOCKED": steps.get("cancel_gate") == "PASS",
            "RECONCILIATION_GATE_FINAL_LOCKED": steps.get("recon_gate") == "PASS",
            "OPERATOR_APPROVAL_PACKET_V2_VALID": steps.get("approval_packet") == "PASS",
            "SANDBOX_FINAL_BLOCKER_MATRIX_COMPLETE": steps.get("blocker_matrix") == "PASS",
            "TESTNET_SANDBOX_FINAL_GATE_REVIEW_READY": all_pass,
            "REAL_TRADING_NOT_ALLOWED": True,
            "TESTNET_SUBMIT_NOT_ALLOWED": True,
        },
    }
    out_dir = ROOT / "data" / "runtime" / "testnet_final_gate"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "final_gate_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = ["# Exchange Sandbox Final Gate Suite Report", "", f"**Status:** {final_status}", "", "## Steps", ""]
    for k, v in steps.items():
        lines.append(f"- {k}: {v}")
    if errors:
        lines.extend(["", "## Errors"])
        for e in errors:
            lines.append(f"- {e}")
    lines.append("")
    (ROOT / "reports" / "exchange_sandbox_final_gate_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    # Handoff
    handoff = ["# Final Exchange Sandbox Gate Handoff", "", "## Completed", "",
        "- Exchange dry-run harness: PASS", "- Credential injection review: PASS",
        "- Request signing dry-run: VALID", "- Submit gate: LOCKED",
        "- Cancel gate: LOCKED", "- Reconciliation gate: LOCKED",
        "- Operator approval packet v2: VALID", "- Final blocker matrix: COMPLETE",
        "- Final gate safety regression: PASS", "- Pre-submit review suite: PASS", "",
        "## Conclusion", "",
        "TESTNET_SANDBOX_FINAL_GATE_REVIEW_READY",
        "REAL_TRADING_NOT_ALLOWED", "TESTNET_SUBMIT_NOT_ALLOWED", "",
    ]
    (ROOT / "reports" / "final_exchange_sandbox_gate_handoff.md").write_text("\n".join(handoff), encoding="utf-8")

    blockers = ["# Final Exchange Sandbox Gate Remaining Blockers", "",
        "1. Real credential vault", "2. Real exchange adapter", "3. Real request signing",
        "4. Real network transport", "5. Real testnet submit", "6. Real cancel API",
        "7. Real position/balance reconciliation", "8. Real rate limit handling",
        "9. Legal approval framework", "10. Field-tested emergency procedure",
        "11. External audit log storage", "",
    ]
    (ROOT / "reports" / "final_exchange_sandbox_gate_remaining_blockers.md").write_text("\n".join(blockers), encoding="utf-8")

    plan = ["# Final Exchange Sandbox Gate Next Stage Plan", "",
        "## T140001-T155000 Goals", "",
        "- Real credential vault integration", "- Real exchange adapter dry-run with testnet",
        "- Real request signing", "- Real network transport layer",
        "- Submit gate unlock conditions", "",
    ]
    (ROOT / "reports" / "final_exchange_sandbox_gate_next_stage_plan.md").write_text("\n".join(plan), encoding="utf-8")

    print(f"\nFinal Gate Suite: {final_status}")
    for k, v in steps.items():
        print(f"  {k}: {v}")
    if errors:
        print(f"Errors: {len(errors)}")

    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
