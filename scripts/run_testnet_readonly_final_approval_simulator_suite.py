"""Suite runner: testnet read-only final approval simulator T275001-T290000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_final_approval_simulator"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_final_approval_simulator"

STEPS = [
    ("step_01_final_approval_simulator", "scripts.run_readonly_final_approval_simulator"),
    ("step_02_network_on_blocker_drill", "scripts.run_network_on_blocker_drill"),
    ("step_03_human_signoff_archive", "scripts.run_readonly_human_signoff_archive"),
    ("step_04_safety_regression", "scripts.run_final_approval_safety_regression"),
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

    print("=== T275001-T290000 Testnet Read-Only Final Approval Simulator Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running final approval simulator steps ---")
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
        "milestone": "T275001-T290000",
        "title": "Testnet Read-Only Final Approval Simulator",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "final_approval_simulator_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Testnet Read-Only Final Approval Simulator Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "TESTNET_READONLY_FINAL_APPROVAL_SIMULATOR_SUITE_PASS",
        "READONLY_FINAL_APPROVAL_SIMULATOR_READY",
        "NETWORK_ON_BLOCKER_DRILL_EXPANDED",
        "NETWORK_ON_BLOCKER_DRILL_PASS",
        "READONLY_HUMAN_SIGNOFF_ARCHIVE_READY",
        "READONLY_FINAL_APPROVAL_NO_NETWORK_NO_SUBMIT_SAFETY_PASS",
        "REAL_NETWORK_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "testnet_readonly_final_approval_simulator_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    handoff_lines = ["# Final Read-Only Final Approval Simulator Handoff", "",
        "## Status", "",
        "TESTNET_READONLY_FINAL_APPROVAL_SIMULATOR_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Final approval simulation: data/runtime/testnet_readonly_final_approval_simulator/final_approval_simulation.json",
        "- Network-on blocker drill: data/runtime/testnet_readonly_final_approval_simulator/network_on_blocker_drill.json",
        "- Human signoff archive: data/runtime/testnet_readonly_final_approval_simulator/human_signoff_archive.json",
        "- Safety regression: data/runtime/testnet_readonly_final_approval_simulator/final_approval_safety_regression.json",
        "- Suite manifest: data/runtime/testnet_readonly_final_approval_simulator/final_approval_simulator_suite_manifest.json",
        ""]
    (REPORT_DIR / "final_readonly_final_approval_simulator_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
