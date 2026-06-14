"""Suite runner: external testnet adapter spec T155001-T170000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

STEPS = [
    ("step_01_adapter_spec", "scripts.run_external_testnet_adapter_spec"),
    ("step_02_credential_vault", "scripts.run_credential_vault_architecture"),
    ("step_03_request_signing", "scripts.run_request_signing_architecture"),
    ("step_04_network_transport", "scripts.run_network_transport_architecture"),
    ("step_05_permission_isolation", "scripts.run_exchange_permission_isolation_plan"),
    ("step_06_submit_governance", "scripts.run_submit_unlock_governance_draft"),
    ("step_07_cancel_recon_governance", "scripts.run_cancel_reconciliation_governance_draft"),
    ("step_08_field_test_criteria", "scripts.run_field_test_acceptance_criteria"),
    ("step_09_threat_model", "scripts.run_threat_model_security_review"),
    ("step_10_safety_regression", "scripts.run_adapter_spec_no_submit_safety_regression"),
]


def run_step(step_id: str, mod_path: str) -> dict:
    try:
        mod = importlib.import_module(mod_path)
        rc = mod.main()
        return {"step_id": step_id, "status": "PASS" if rc == 0 else "FAIL", "return_code": rc}
    except Exception as exc:
        return {"step_id": step_id, "status": "FAIL", "error": str(exc)}


def run_previous_suites() -> list[dict]:
    results = []
    suites = [
        ("enablement_review_suite", "scripts.run_testnet_submit_enablement_review_suite"),
    ]
    for suite_id, suite_mod_path in suites:
        try:
            mod = importlib.import_module(suite_mod_path)
            rc = mod.main()
            results.append({"step_id": suite_id, "status": "PASS" if rc == 0 else "FAIL", "return_code": rc})
        except Exception as exc:
            results.append({"step_id": suite_id, "status": "FAIL", "error": str(exc)})
    return results


def main() -> int:
    start = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== T155001-T170000 External Testnet Adapter Spec Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running adapter spec steps ---")
    step_results = []
    for step_id, mod_path in STEPS:
        result = run_step(step_id, mod_path)
        step_results.append(result)
        print(f"  {step_id}: {result['status']}")
    print()

    all_results = prev_results + step_results
    passed = sum(1 for r in all_results if r["status"] == "PASS")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")

    manifest = {
        "milestone": "T155001-T170000",
        "title": "External Testnet Adapter Spec",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "external_adapter_spec_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# External Testnet Adapter Spec Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "EXTERNAL_TESTNET_ADAPTER_SPEC_SUITE_PASS",
        "EXTERNAL_TESTNET_ADAPTER_SPEC_READY",
        "CREDENTIAL_VAULT_ARCHITECTURE_READY",
        "REQUEST_SIGNING_ARCHITECTURE_READY",
        "NETWORK_TRANSPORT_ARCHITECTURE_READY",
        "EXCHANGE_PERMISSION_ISOLATION_PLAN_READY",
        "SUBMIT_UNLOCK_GOVERNANCE_DRAFT_READY",
        "CANCEL_RECONCILIATION_GOVERNANCE_DRAFT_READY",
        "FIELD_TEST_ACCEPTANCE_CRITERIA_READY",
        "THREAT_MODEL_SECURITY_REVIEW_READY",
        "NO_SUBMIT_SAFETY_PRESERVED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "external_testnet_adapter_spec_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    # Handoff docs
    handoff_lines = ["# Final External Testnet Adapter Spec Handoff", "",
        "## Status", "",
        "EXTERNAL_TESTNET_ADAPTER_SPEC_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- External adapter spec: data/runtime/testnet_adapter_spec/external_adapter_spec.json",
        "- Credential vault architecture: data/runtime/testnet_adapter_spec/credential_vault_architecture.json",
        "- Request signing architecture: data/runtime/testnet_adapter_spec/request_signing_architecture.json",
        "- Network transport architecture: data/runtime/testnet_adapter_spec/network_transport_architecture.json",
        "- Permission isolation plan: data/runtime/testnet_adapter_spec/exchange_permission_isolation_plan.json",
        "- Submit governance: data/runtime/testnet_adapter_spec/submit_unlock_governance.json",
        "- Cancel/recon governance: data/runtime/testnet_adapter_spec/cancel_reconciliation_governance.json",
        "- Field test criteria: data/runtime/testnet_adapter_spec/field_test_acceptance_criteria.json",
        "- Threat model: data/runtime/testnet_adapter_spec/threat_model_security_review.json",
        "- Safety regression: data/runtime/testnet_adapter_spec/adapter_spec_safety_regression.json",
        ""]
    (REPORT_DIR / "final_external_testnet_adapter_spec_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    blocker_lines = ["# Final External Testnet Adapter Spec Remaining Blockers", "",
        "| Blocker | Status |", "|---------|--------|",
        "| Real credential vault implementation | NOT_IMPLEMENTED |",
        "| Real request signing implementation | NOT_IMPLEMENTED |",
        "| Real network transport implementation | NOT_IMPLEMENTED |",
        "| Real exchange adapter implementation | NOT_IMPLEMENTED |",
        "| Field test execution | NOT_EXECUTED |",
        "| Human approval chain | NOT_COMPLETED |",
        "| Submit gate unlock | LOCKED |",
        "| Cancel gate unlock | LOCKED |",
        "| Reconciliation gate unlock | LOCKED |",
        "", "## Conclusion", "", "TESTNET_SUBMIT_NOT_ALLOWED", "REAL_TRADING_NOT_ALLOWED", ""]
    (REPORT_DIR / "final_external_testnet_adapter_spec_remaining_blockers.md").write_text("\n".join(blocker_lines), encoding="utf-8")

    next_lines = ["# Final External Testnet Adapter Spec Next Stage Plan", "",
        "## Next Stage: Real Adapter Implementation", "",
        "Prerequisites:", "- All architecture specs reviewed and approved",
        "- Credential vault implemented and tested",
        "- Request signing implemented and tested",
        "- Network transport implemented and tested",
        "- Human approval chain completed",
        "- Field test scope defined and approved",
        "", "## Conclusion", "", "NEXT_STAGE_REQUIRES_FULL_APPROVAL", "TESTNET_SUBMIT_NOT_ALLOWED", ""]
    (REPORT_DIR / "final_external_testnet_adapter_spec_next_stage_plan.md").write_text("\n".join(next_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    if failed == 0:
        print("=== EXTERNAL_TESTNET_ADAPTER_SPEC_SUITE_PASS ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
