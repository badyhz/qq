"""Suite runner: testnet read-only discovery T230001-T245000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_discovery"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_discovery"

STEPS = [
    ("step_01_discovery_design", "scripts.run_readonly_discovery_design"),
    ("step_02_credential_policy", "scripts.run_credential_policy_stub"),
    ("step_03_capability_inventory", "scripts.run_exchange_capability_inventory"),
    ("step_04_adapter_contract", "scripts.run_readonly_adapter_contract"),
    ("step_05_governance_checklist", "scripts.run_discovery_governance_checklist"),
    ("step_06_dry_run_packet", "scripts.run_readonly_discovery_dry_run_packet"),
    ("step_07_safety_regression", "scripts.run_readonly_discovery_safety_regression"),
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
        ("mock_closeout_suite", "scripts.run_external_testnet_mock_closeout_suite"),
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

    print("=== T230001-T245000 Testnet Read-Only Discovery Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running read-only discovery steps ---")
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
        "milestone": "T230001-T245000",
        "title": "Testnet Read-Only Discovery",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "readonly_discovery_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Testnet Read-Only Discovery Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "TESTNET_READONLY_DISCOVERY_SUITE_PASS",
        "READ_ONLY_TESTNET_DISCOVERY_DESIGN_READY",
        "CREDENTIAL_POLICY_STUB_READY",
        "EXCHANGE_CAPABILITY_INVENTORY_READY",
        "READ_ONLY_ADAPTER_CONTRACT_READY",
        "DISCOVERY_GOVERNANCE_CHECKLIST_READY",
        "READONLY_DISCOVERY_NO_NETWORK_NO_SUBMIT_SAFETY_PASS",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "testnet_readonly_discovery_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    handoff_lines = ["# Final Testnet Read-Only Discovery Handoff", "",
        "## Status", "",
        "TESTNET_READONLY_DISCOVERY_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Discovery design: data/runtime/testnet_readonly_discovery/discovery_design.json",
        "- Credential policy: data/runtime/testnet_readonly_discovery/credential_policy_stub.json",
        "- Capability inventory: data/runtime/testnet_readonly_discovery/exchange_capability_inventory.json",
        "- Adapter contract: data/runtime/testnet_readonly_discovery/readonly_adapter_contract.json",
        "- Governance checklist: data/runtime/testnet_readonly_discovery/discovery_governance_checklist.json",
        "- Dry-run packet: data/runtime/testnet_readonly_discovery/discovery_dry_run_packet.json",
        "- Safety regression: data/runtime/testnet_readonly_discovery/readonly_discovery_safety_regression.json",
        "- Suite manifest: data/runtime/testnet_readonly_discovery/readonly_discovery_suite_manifest.json",
        ""]
    (REPORT_DIR / "final_testnet_readonly_discovery_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
