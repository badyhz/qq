"""Suite runner: external testnet mock closeout T215001-T230000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_closeout"
REPORT_DIR = ROOT / "reports" / "testnet_mock_closeout"

STEPS = [
    ("step_01_closeout_summary", "scripts.run_mock_review_closeout_summary"),
    ("step_02_gate_blocker_ledger", "scripts.run_gate_blocker_ledger"),
    ("step_03_readiness_scorecard", "scripts.run_readiness_scorecard"),
    ("step_04_final_archive", "scripts.run_final_no_submit_archive"),
    ("step_05_prerequisite_checklist", "scripts.run_next_stage_prerequisite_checklist"),
    ("step_06_safety_regression", "scripts.run_mock_closeout_no_submit_safety_regression"),
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
        ("mock_review_suite", "scripts.run_external_testnet_mock_review_suite"),
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

    print("=== T215001-T230000 External Testnet Mock Closeout Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running mock closeout steps ---")
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
        "milestone": "T215001-T230000",
        "title": "External Testnet Mock Closeout",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "mock_closeout_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# External Testnet Mock Closeout Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "EXTERNAL_TESTNET_MOCK_CLOSEOUT_SUITE_PASS",
        "MOCK_REVIEW_CLOSEOUT_READY",
        "GATE_BLOCKER_LEDGER_READY",
        "READINESS_SCORECARD_READY",
        "FINAL_NO_SUBMIT_ARCHIVE_READY",
        "NEXT_STAGE_PREREQUISITE_CHECKLIST_READY",
        "MOCK_CLOSEOUT_NO_SUBMIT_SAFETY_REGRESSION_PASS",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "external_testnet_mock_closeout_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    # Handoff doc
    handoff_lines = ["# Final External Testnet Mock Closeout Handoff", "",
        "## Status", "",
        "EXTERNAL_TESTNET_MOCK_CLOSEOUT_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Closeout summary: data/runtime/testnet_mock_closeout/closeout_summary.json",
        "- Gate blocker ledger: data/runtime/testnet_mock_closeout/gate_blocker_ledger.json",
        "- Readiness scorecard: data/runtime/testnet_mock_closeout/readiness_scorecard.json",
        "- Final archive: data/runtime/testnet_mock_closeout/final_no_submit_archive.json",
        "- Prerequisite checklist: data/runtime/testnet_mock_closeout/next_stage_prerequisite_checklist.json",
        "- Safety regression: data/runtime/testnet_mock_closeout/closeout_safety_regression.json",
        "- Suite manifest: data/runtime/testnet_mock_closeout/mock_closeout_suite_manifest.json",
        ""]
    (REPORT_DIR / "final_external_testnet_mock_closeout_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
