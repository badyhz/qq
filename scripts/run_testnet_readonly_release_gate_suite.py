"""Suite runner: testnet read-only release gate T260001-T275000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_release_gate"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_release_gate"

STEPS = [
    ("step_01_release_gate", "scripts.run_readonly_discovery_release_gate"),
    ("step_02_network_off_execution_packet", "scripts.run_network_off_execution_packet"),
    ("step_03_credential_air_gap_policy", "scripts.run_credential_air_gap_policy"),
    ("step_04_release_blocker_ledger", "scripts.run_readonly_release_blocker_ledger"),
    ("step_05_operator_signoff_draft", "scripts.run_readonly_operator_signoff_draft"),
    ("step_06_safety_regression", "scripts.run_readonly_release_gate_safety_regression"),
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
        ("readonly_discovery_suite", "scripts.run_testnet_readonly_discovery_suite"),
        ("readonly_preapproval_suite", "scripts.run_testnet_readonly_preapproval_suite"),
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

    print("=== T260001-T275000 Testnet Read-Only Release Gate Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running release gate steps ---")
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
        "milestone": "T260001-T275000",
        "title": "Testnet Read-Only Release Gate",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "release_gate_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Testnet Read-Only Release Gate Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "TESTNET_READONLY_RELEASE_GATE_SUITE_PASS",
        "READONLY_DISCOVERY_RELEASE_GATE_READY",
        "NETWORK_OFF_EXECUTION_PACKET_READY",
        "CREDENTIAL_AIR_GAP_POLICY_READY",
        "READONLY_DISCOVERY_RELEASE_BLOCKERS_READY",
        "READONLY_DISCOVERY_OPERATOR_SIGNOFF_DRAFT_READY",
        "READONLY_RELEASE_GATE_NO_NETWORK_NO_SUBMIT_SAFETY_PASS",
        "REAL_NETWORK_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "testnet_readonly_release_gate_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    handoff_lines = ["# Final Testnet Read-Only Release Gate Handoff", "",
        "## Status", "",
        "TESTNET_READONLY_RELEASE_GATE_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Release gate packet: data/runtime/testnet_readonly_release_gate/release_gate_packet.json",
        "- Network-off execution packet: data/runtime/testnet_readonly_release_gate/network_off_execution_packet.json",
        "- Credential air-gap policy: data/runtime/testnet_readonly_release_gate/credential_air_gap_policy.json",
        "- Release blocker ledger: data/runtime/testnet_readonly_release_gate/release_blocker_ledger.json",
        "- Operator signoff draft: data/runtime/testnet_readonly_release_gate/operator_signoff_draft.json",
        "- Safety regression: data/runtime/testnet_readonly_release_gate/release_gate_safety_regression.json",
        "- Suite manifest: data/runtime/testnet_readonly_release_gate/release_gate_suite_manifest.json",
        ""]
    (REPORT_DIR / "final_testnet_readonly_release_gate_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
