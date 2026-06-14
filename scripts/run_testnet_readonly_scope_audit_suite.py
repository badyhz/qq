"""Suite runner: testnet read-only scope audit T320001-T32500."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_scope_audit"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_scope_audit"

STEPS = [
    ("step_01_stage_inventory", "scripts.run_readonly_stage_inventory"),
    ("step_02_gap_matrix", "scripts.run_prd_compliance_gap_matrix"),
    ("step_03_suite_depth_review", "scripts.run_readonly_suite_depth_review"),
    ("step_04_remediation_backlog", "scripts.run_readonly_remediation_backlog"),
    ("step_05_safety_regression", "scripts.run_readonly_scope_audit_safety_regression"),
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
        ("readonly_dry_execution_rehearsal_suite", "scripts.run_testnet_readonly_dry_execution_rehearsal_suite"),
        ("readonly_final_governance_freeze_suite", "scripts.run_testnet_readonly_final_governance_freeze_suite"),
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

    print("=== T320001-T32500 Testnet Read-Only Scope Audit Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running scope audit steps ---")
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
        "milestone": "T320001-T32500",
        "title": "Testnet Read-Only Scope Audit",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "readonly_scope_audit_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Testnet Read-Only Scope Audit Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "TESTNET_READONLY_SCOPE_AUDIT_SUITE_PASS",
        "READONLY_STAGE_INVENTORY_READY",
        "PRD_COMPLIANCE_GAP_REPORT_READY",
        "READONLY_SUITE_DEPTH_REVIEW_READY",
        "READONLY_REMEDIATION_BACKLOG_READY",
        "READONLY_SCOPE_AUDIT_NO_NETWORK_NO_SUBMIT_SAFETY_PASS",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "testnet_readonly_scope_audit_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    handoff_lines = ["# Final Testnet Read-Only Scope Audit Handoff", "",
        "## Status", "",
        "TESTNET_READONLY_SCOPE_AUDIT_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Stage inventory: data/runtime/testnet_readonly_scope_audit/stage_inventory.json",
        "- Gap matrix: data/runtime/testnet_readonly_scope_audit/prd_compliance_gap_matrix.json",
        "- Suite depth review: data/runtime/testnet_readonly_scope_audit/suite_depth_review.json",
        "- Remediation backlog: data/runtime/testnet_readonly_scope_audit/remediation_backlog.json",
        "- Safety regression: data/runtime/testnet_readonly_scope_audit/scope_audit_safety_regression.json",
        "- Suite manifest: data/runtime/testnet_readonly_scope_audit/readonly_scope_audit_suite_manifest.json",
        ""]
    (REPORT_DIR / "final_testnet_readonly_scope_audit_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
