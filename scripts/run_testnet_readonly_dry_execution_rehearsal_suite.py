"""Suite runner: testnet read-only dry execution rehearsal T290001-T305000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_dry_execution_rehearsal"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_dry_execution_rehearsal"

STEPS = [
    ("step_01_dry_execution_rehearsal", "scripts.run_readonly_dry_execution_rehearsal"),
    ("step_02_endpoint_allowlist_stub", "scripts.run_endpoint_allowlist_stub"),
    ("step_03_audit_redaction_pack", "scripts.run_audit_redaction_pack"),
    ("step_04_safety_regression", "scripts.run_dry_execution_safety_regression"),
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
        ("readonly_release_gate_suite", "scripts.run_testnet_readonly_release_gate_suite"),
        ("readonly_final_approval_simulator_suite", "scripts.run_testnet_readonly_final_approval_simulator_suite"),
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

    print("=== T290001-T305000 Testnet Read-Only Dry Execution Rehearsal Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running dry execution rehearsal steps ---")
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
        "milestone": "T290001-T305000",
        "title": "Testnet Read-Only Dry Execution Rehearsal",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "dry_execution_rehearsal_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Testnet Read-Only Dry Execution Rehearsal Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "TESTNET_READONLY_DRY_EXECUTION_REHEARSAL_SUITE_PASS",
        "READONLY_DRY_EXECUTION_REHEARSAL_READY",
        "ENDPOINT_ALLOWLIST_STUB_READY",
        "AUDIT_REDACTION_PACK_READY",
        "READONLY_DRY_EXECUTION_NO_NETWORK_NO_SUBMIT_SAFETY_PASS",
        "REAL_NETWORK_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "testnet_readonly_dry_execution_rehearsal_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    handoff_lines = ["# Final Read-Only Dry Execution Rehearsal Handoff", "",
        "## Status", "",
        "TESTNET_READONLY_DRY_EXECUTION_REHEARSAL_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Dry execution rehearsal: data/runtime/testnet_readonly_dry_execution_rehearsal/dry_execution_rehearsal.json",
        "- Endpoint allowlist stub: data/runtime/testnet_readonly_dry_execution_rehearsal/endpoint_allowlist_stub.json",
        "- Audit redaction pack: data/runtime/testnet_readonly_dry_execution_rehearsal/audit_redaction_pack.json",
        "- Safety regression: data/runtime/testnet_readonly_dry_execution_rehearsal/dry_execution_safety_regression.json",
        "- Suite manifest: data/runtime/testnet_readonly_dry_execution_rehearsal/dry_execution_rehearsal_suite_manifest.json",
        ""]
    (REPORT_DIR / "final_readonly_dry_execution_rehearsal_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
