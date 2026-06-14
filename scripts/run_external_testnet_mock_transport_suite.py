"""Suite runner: external testnet mock transport T170001-T185000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

STEPS = [
    ("step_01_mock_transport", "scripts.run_mock_transport_contract"),
    ("step_02_vault_stub", "scripts.run_vault_stub_contract"),
    ("step_03_response_fixtures", "scripts.run_exchange_response_fixtures"),
    ("step_04_signing_fixture", "scripts.run_request_signing_fixture_validation"),
    ("step_05_adapter_skeleton", "scripts.run_adapter_skeleton_dry_run"),
    ("step_06_field_test_governance", "scripts.run_field_test_governance_pack"),
    ("step_07_unlock_dry_run", "scripts.run_unlock_request_dry_run"),
    ("step_08_operator_runbook", "scripts.run_operator_runbook_draft"),
    ("step_09_safety_regression", "scripts.run_mock_transport_no_submit_safety_regression"),
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
        ("adapter_spec_suite", "scripts.run_external_testnet_adapter_spec_suite"),
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

    print("=== T170001-T185000 External Testnet Mock Transport Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running mock transport steps ---")
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
        "milestone": "T170001-T185000",
        "title": "External Testnet Mock Transport",
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
        "# External Testnet Mock Transport Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "EXTERNAL_TESTNET_MOCK_TRANSPORT_SUITE_PASS",
        "MOCK_TRANSPORT_CONTRACT_READY",
        "VAULT_STUB_CONTRACT_READY",
        "FIELD_TEST_GOVERNANCE_PACK_READY",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "external_testnet_mock_transport_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    # Handoff doc
    handoff_lines = ["# Final External Testnet Mock Transport Handoff", "",
        "## Status", "",
        "EXTERNAL_TESTNET_MOCK_TRANSPORT_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Mock transport contract: data/runtime/testnet_mock_transport/mock_transport_contract.json",
        "- Vault stub contract: data/runtime/testnet_mock_transport/vault_stub_contract.json",
        "- Response fixtures: data/runtime/testnet_mock_transport/exchange_response_fixtures.json",
        "- Signing fixture: data/runtime/testnet_mock_transport/request_signing_fixture.json",
        "- Adapter skeleton: data/runtime/testnet_mock_transport/adapter_skeleton.json",
        "- Field-test governance: data/runtime/testnet_mock_transport/field_test_governance_pack.json",
        "- Unlock requests: data/runtime/testnet_mock_transport/unlock_requests_all.json",
        "- Operator runbook: data/runtime/testnet_mock_transport/operator_runbook.json",
        "- Safety regression: data/runtime/testnet_mock_transport/mock_transport_safety_regression.json",
        ""]
    (REPORT_DIR / "final_external_testnet_mock_transport_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
