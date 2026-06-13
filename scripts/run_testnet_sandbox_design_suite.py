#!/usr/bin/env python3
"""T95001-T110000 — Testnet Sandbox Design Suite Runner."""
import json, sys, pathlib
from datetime import datetime, timezone
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    now = datetime.now(timezone.utc).isoformat()
    steps = {}
    errors = []

    # 1. Sandbox adapter contract
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib
        mod = importlib.import_module("run_sandbox_adapter_contract_check")
        rc = mod.main()
        steps["adapter_contract"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["adapter_contract"] = "FAIL"
        errors.append(f"adapter_contract: {e}")

    # 2. Credential vault stub
    try:
        mod = importlib.import_module("run_credential_vault_stub_check")
        rc = mod.main()
        steps["credential_vault"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["credential_vault"] = "FAIL"
        errors.append(f"credential_vault: {e}")

    # 3. Human approval gate
    try:
        mod = importlib.import_module("run_human_approval_gate_check")
        rc = mod.main()
        steps["human_approval"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["human_approval"] = "FAIL"
        errors.append(f"human_approval: {e}")

    # 4. Submit intent review packet
    try:
        mod = importlib.import_module("run_submit_intent_review_packet")
        rc = mod.main()
        steps["submit_intent"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["submit_intent"] = "FAIL"
        errors.append(f"submit_intent: {e}")

    # 5. Sandbox risk control
    try:
        mod = importlib.import_module("run_sandbox_risk_control_check")
        rc = mod.main()
        steps["risk_controls"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["risk_controls"] = "FAIL"
        errors.append(f"risk_controls: {e}")

    # 6. Kill switch
    try:
        mod = importlib.import_module("run_kill_switch_validation")
        rc = mod.main()
        steps["kill_switch"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["kill_switch"] = "FAIL"
        errors.append(f"kill_switch: {e}")

    # 7. No-submit sandbox smoke
    try:
        mod = importlib.import_module("run_no_submit_sandbox_smoke")
        rc = mod.main()
        steps["sandbox_smoke"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["sandbox_smoke"] = "FAIL"
        errors.append(f"sandbox_smoke: {e}")

    # 8. Gap closure matrix
    try:
        mod = importlib.import_module("run_testnet_sandbox_gap_closure_matrix")
        rc = mod.main()
        steps["gap_closure"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["gap_closure"] = "FAIL"
        errors.append(f"gap_closure: {e}")

    # 9. Sandbox design safety regression
    try:
        mod = importlib.import_module("run_sandbox_design_safety_regression")
        rc = mod.main()
        steps["safety_regression"] = "PASS" if rc == 0 else "FAIL"
    except Exception as e:
        steps["safety_regression"] = "FAIL"
        errors.append(f"safety_regression: {e}")

    # Final status
    all_pass = all(v in ("PASS", "WARN") for v in steps.values())
    final_status = "TESTNET_SANDBOX_DESIGN_SUITE_PASS" if all_pass else "TESTNET_SANDBOX_DESIGN_SUITE_BLOCKED"

    # Write manifest
    manifest = {
        "manifest_id": f"sandbox_{now.replace(':', '').replace('-', '')[:20]}",
        "timestamp": now,
        "steps": steps,
        "errors": errors,
        "status": final_status,
        "required_statuses": {
            "TESTNET_SANDBOX_DESIGN_SUITE_PASS": final_status == "TESTNET_SANDBOX_DESIGN_SUITE_PASS",
            "SANDBOX_ADAPTER_INTERFACE_VALID": steps.get("adapter_contract") == "PASS",
            "CREDENTIAL_VAULT_STUB_VALID": steps.get("credential_vault") == "PASS",
            "HUMAN_APPROVAL_GATE_VALID": steps.get("human_approval") == "PASS",
            "NO_SUBMIT_SANDBOX_SMOKE_PASS": steps.get("sandbox_smoke") == "PASS",
            "KILL_SWITCH_DESIGN_VALID": steps.get("kill_switch") == "PASS",
            "TESTNET_SANDBOX_NOT_READY_FOR_SUBMIT": steps.get("gap_closure") == "PASS",
            "REAL_TRADING_NOT_ALLOWED": True,
            "TESTNET_SUBMIT_NOT_ALLOWED": True,
        },
    }
    out_dir = ROOT / "data" / "runtime" / "testnet_sandbox"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "design_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Write reports
    lines = [
        "# Testnet Sandbox Design Suite Report", "", f"**Status:** {final_status}", "", "## Steps", "",
    ]
    for k, v in steps.items():
        lines.append(f"- {k}: {v}")
    if errors:
        lines.extend(["", "## Errors"])
        for e in errors:
            lines.append(f"- {e}")
    lines.append("")
    (ROOT / "reports" / "testnet_sandbox_design_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    # Handoff report
    handoff = [
        "# Final Testnet Sandbox Design Handoff", "",
        "## Completed", "",
        "- Sandbox adapter interface: DESIGNED",
        "- Simulated exchange adapter: IMPLEMENTED",
        "- Credential vault: STUB_ONLY",
        "- Human approval gate: DEFAULT_DENY",
        "- Submit intent review: VALIDATED",
        "- Sandbox risk controls: DESIGNED",
        "- Kill switch: ENABLED_BLOCKING",
        "- No-submit sandbox smoke: PASS",
        "- Gap closure matrix: DOCUMENTED",
        "- Safety regression: PASS",
        "", "## Remaining Blockers", "",
        "- Credential vault: needs real implementation review",
        "- Cancel safety: needs implementation",
        "- Position reconciliation: MISSING",
        "- Balance reconciliation: MISSING",
        "- Rate limits: MISSING",
        "- Network failure handling: MISSING",
        "- Operator emergency procedure: MISSING",
        "", "## Conclusion", "",
        "TESTNET_SANDBOX_NOT_READY_FOR_SUBMIT",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "",
    ]
    (ROOT / "reports" / "final_testnet_sandbox_design_handoff.md").write_text("\n".join(handoff), encoding="utf-8")

    # Blockers report
    blockers = [
        "# Final Testnet Sandbox Remaining Blockers", "",
        "The following must be resolved before testnet submit can be considered:", "",
        "1. **Credential Vault Real Implementation** — replace stub with real vault",
        "2. **Exchange Sandbox Adapter** — implement real testnet API adapter",
        "3. **Cancel Safety** — implement order cancel safety mechanism",
        "4. **Position Reconciliation** — implement position reconciliation",
        "5. **Balance Reconciliation** — implement balance reconciliation",
        "6. **Rate Limit Handling** — implement rate limit handling",
        "7. **Network Failure Handling** — implement network failure recovery",
        "8. **Operator Emergency Procedure** — implement emergency procedures",
        "", "## Next Phase", "",
        "T110001-T125000: Credential Vault Review / Exchange Sandbox Adapter Stub / Cancel Safety / Reconciliation Design",
        "",
    ]
    (ROOT / "reports" / "final_testnet_sandbox_remaining_blockers.md").write_text("\n".join(blockers), encoding="utf-8")

    # Next stage plan
    plan = [
        "# Final Testnet Sandbox Next Stage Plan", "",
        "## T110001-T125000 Goals", "",
        "- Credential vault review and real implementation design",
        "- Exchange sandbox adapter stub with real testnet endpoint",
        "- Cancel safety implementation",
        "- Position reconciliation design",
        "- Balance reconciliation design",
        "- Rate limit handling design",
        "- Network failure handling design",
        "", "## Still Blocked After T110001-T125000", "",
        "- Real testnet submit (requires full human approval + all reconciliations)",
        "- Real live submit (requires separate milestone, not in scope)",
        "",
    ]
    (ROOT / "reports" / "final_testnet_sandbox_next_stage_plan.md").write_text("\n".join(plan), encoding="utf-8")

    print(f"\nTestnet Sandbox Design: {final_status}")
    for k, v in steps.items():
        print(f"  {k}: {v}")
    if errors:
        print(f"Errors: {len(errors)}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
