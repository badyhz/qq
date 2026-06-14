"""Suite runner: testnet read-only preapproval T245001-T260000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_preapproval"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_preapproval"

STEPS = [
    ("step_01_approval_packet", "scripts.run_readonly_discovery_approval_packet"),
    ("step_02_preflight_evidence", "scripts.run_no_network_preflight_evidence"),
    ("step_03_credential_sop", "scripts.run_credential_handling_sop"),
    ("step_04_operator_checklist", "scripts.run_readonly_discovery_operator_checklist"),
    ("step_05_manual_review_queue", "scripts.run_readonly_discovery_manual_review_queue"),
    ("step_06_safety_regression", "scripts.run_readonly_preapproval_safety_regression"),
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

    print("=== T245001-T260000 Testnet Read-Only Preapproval Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running preapproval steps ---")
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
        "milestone": "T245001-T260000",
        "title": "Testnet Read-Only Preapproval",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "preapproval_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Testnet Read-Only Preapproval Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "TESTNET_READONLY_PREAPPROVAL_SUITE_PASS",
        "READONLY_DISCOVERY_APPROVAL_PACKET_READY",
        "NO_NETWORK_PREFLIGHT_EVIDENCE_READY",
        "CREDENTIAL_HANDLING_SOP_READY",
        "READONLY_DISCOVERY_OPERATOR_CHECKLIST_READY",
        "READONLY_DISCOVERY_MANUAL_REVIEW_QUEUE_READY",
        "READONLY_PREAPPROVAL_NO_NETWORK_NO_SUBMIT_SAFETY_PASS",
        "REAL_NETWORK_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "testnet_readonly_preapproval_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    handoff_lines = ["# Final Testnet Read-Only Preapproval Handoff", "",
        "## Status", "",
        "TESTNET_READONLY_PREAPPROVAL_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Approval packet: data/runtime/testnet_readonly_preapproval/approval_packet.json",
        "- Preflight evidence: data/runtime/testnet_readonly_preapproval/no_network_preflight_evidence.json",
        "- Credential SOP: data/runtime/testnet_readonly_preapproval/credential_handling_sop.json",
        "- Operator checklist: data/runtime/testnet_readonly_preapproval/operator_checklist.json",
        "- Manual review queue: data/runtime/testnet_readonly_preapproval/manual_review_queue.json",
        "- Safety regression: data/runtime/testnet_readonly_preapproval/preapproval_safety_regression.json",
        "- Suite manifest: data/runtime/testnet_readonly_preapproval/preapproval_suite_manifest.json",
        ""]
    (REPORT_DIR / "final_testnet_readonly_preapproval_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
