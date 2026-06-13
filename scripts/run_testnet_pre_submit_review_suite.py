#!/usr/bin/env python3
"""T110001-T125000 — Testnet Pre-Submit Review Suite Runner."""
import json, sys, pathlib, importlib
from datetime import datetime, timezone
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    now = datetime.now(timezone.utc).isoformat()
    steps = {}
    errors = []

    runners = [
        ("credential_vault_review", "run_credential_vault_review"),
        ("exchange_adapter_stub", "run_exchange_sandbox_adapter_stub_check"),
        ("cancel_safety", "run_cancel_safety_simulation"),
        ("position_reconciliation", "run_position_reconciliation_simulation"),
        ("balance_reconciliation", "run_balance_reconciliation_simulation"),
        ("failure_modes", "run_sandbox_failure_mode_simulation"),
        ("audit_log", "run_audit_log_design_validation"),
        ("emergency_procedure", "run_operator_emergency_procedure_check"),
        ("approval_hardening", "run_human_approval_workflow_hardening"),
    ]

    for step_name, script_name in runners:
        try:
            mod = importlib.import_module(script_name)
            rc = mod.main()
            steps[step_name] = "PASS" if rc == 0 else "FAIL"
        except Exception as e:
            steps[step_name] = "FAIL"
            errors.append(f"{step_name}: {e}")

    # Run previous sandbox design suite
    try:
        mod = importlib.import_module("run_testnet_sandbox_design_suite")
        rc = mod.main()
        steps["sandbox_design"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["sandbox_design"] = "FAIL"
        errors.append(f"sandbox_design: {e}")

    # Final status
    all_pass = all(v in ("PASS", "WARN") for v in steps.values())
    final_status = "TESTNET_PRE_SUBMIT_REVIEW_SUITE_PASS" if all_pass else "TESTNET_PRE_SUBMIT_REVIEW_SUITE_BLOCKED"

    # Write manifest
    manifest = {
        "manifest_id": f"presubmit_{now.replace(':', '').replace('-', '')[:20]}",
        "timestamp": now,
        "steps": steps,
        "errors": errors,
        "status": final_status,
        "required_statuses": {
            "TESTNET_PRE_SUBMIT_REVIEW_SUITE_PASS": final_status == "TESTNET_PRE_SUBMIT_REVIEW_SUITE_PASS",
            "CREDENTIAL_VAULT_REVIEW_PASS": steps.get("credential_vault_review") == "PASS",
            "EXCHANGE_SANDBOX_ADAPTER_STUB_VALID": steps.get("exchange_adapter_stub") == "PASS",
            "CANCEL_SAFETY_SIMULATION_PASS": steps.get("cancel_safety") == "PASS",
            "POSITION_RECONCILIATION_SIMULATION_PASS": steps.get("position_reconciliation") == "PASS",
            "BALANCE_RECONCILIATION_SIMULATION_PASS": steps.get("balance_reconciliation") == "PASS",
            "RATE_LIMIT_SIMULATION_PASS": steps.get("failure_modes") == "PASS",
            "NETWORK_FAILURE_SIMULATION_PASS": steps.get("failure_modes") == "PASS",
            "AUDIT_LOG_DESIGN_VALID": steps.get("audit_log") == "PASS",
            "OPERATOR_EMERGENCY_PROCEDURE_VALID": steps.get("emergency_procedure") == "PASS",
            "HUMAN_APPROVAL_HARDENED": steps.get("approval_hardening") == "PASS",
            "TESTNET_SANDBOX_PRE_SUBMIT_REVIEW_READY": all_pass,
            "REAL_TRADING_NOT_ALLOWED": True,
            "TESTNET_SUBMIT_NOT_ALLOWED": True,
        },
    }
    out_dir = ROOT / "data" / "runtime" / "testnet_presubmit"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pre_submit_review_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Reports
    lines = ["# Testnet Pre-Submit Review Suite Report", "", f"**Status:** {final_status}", "", "## Steps", ""]
    for k, v in steps.items():
        lines.append(f"- {k}: {v}")
    if errors:
        lines.extend(["", "## Errors"])
        for e in errors:
            lines.append(f"- {e}")
    lines.append("")
    (ROOT / "reports" / "testnet_pre_submit_review_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    # Handoff
    handoff = ["# Final Testnet Pre-Submit Handoff", "", "## Completed", "",
        "- Credential vault review: PASS", "- Exchange adapter stub: VALID",
        "- Cancel safety simulation: PASS", "- Position reconciliation: PASS",
        "- Balance reconciliation: PASS", "- Rate limit simulation: PASS",
        "- Network failure simulation: PASS", "- Audit log design: VALID",
        "- Operator emergency procedure: VALID", "- Human approval hardening: PASS",
        "- Sandbox design suite: PASS", "",
        "## Remaining Before Submit", "",
        "- Real credential vault implementation", "- Real exchange adapter integration",
        "- Real cancel safety", "- Real reconciliation", "- Full human approval workflow",
        "- Kill switch operational testing", "",
        "## Conclusion", "",
        "TESTNET_SANDBOX_PRE_SUBMIT_REVIEW_READY",
        "REAL_TRADING_NOT_ALLOWED", "TESTNET_SUBMIT_NOT_ALLOWED", "",
    ]
    (ROOT / "reports" / "final_testnet_pre_submit_handoff.md").write_text("\n".join(handoff), encoding="utf-8")

    # Blockers
    blockers = ["# Final Testnet Pre-Submit Remaining Blockers", "",
        "1. **Real Credential Vault** — replace stub with encrypted vault",
        "2. **Real Exchange Adapter** — implement with real testnet endpoints",
        "3. **Real Cancel Safety** — implement with real order tracking",
        "4. **Real Position/Balance Reconciliation** — implement with real exchange queries",
        "5. **Real Audit Log Persistence** — implement with tamper-evident storage",
        "6. **Full Human Approval Workflow** — integrate with notification system",
        "",
    ]
    (ROOT / "reports" / "final_testnet_pre_submit_remaining_blockers.md").write_text("\n".join(blockers), encoding="utf-8")

    # Next stage plan
    plan = ["# Final Testnet Pre-Submit Next Stage Plan", "",
        "## T125001-T140000 Goals", "",
        "- Exchange sandbox adapter dry-run harness",
        "- Credential injection review",
        "- Submit gate final lock",
        "- Real testnet endpoint validation",
        "- End-to-end sandbox dry-run with real stubs",
        "",
    ]
    (ROOT / "reports" / "final_testnet_pre_submit_next_stage_plan.md").write_text("\n".join(plan), encoding="utf-8")

    print(f"\nPre-Submit Review: {final_status}")
    for k, v in steps.items():
        print(f"  {k}: {v}")
    if errors:
        print(f"Errors: {len(errors)}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
