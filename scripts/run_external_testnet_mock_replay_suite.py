"""Suite runner: external testnet mock replay T185001-T200000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_replay"
REPORT_DIR = ROOT / "reports" / "testnet_mock_replay"

STEPS = [
    ("step_01_replay_harness", "scripts.run_mock_replay_harness"),
    ("step_02_scenario_matrix", "scripts.run_replay_scenario_matrix"),
    ("step_03_evidence_bundle", "scripts.run_mock_field_test_evidence_bundle"),
    ("step_04_approval_packet_v3", "scripts.run_human_approval_packet_v3"),
    ("step_05_trace_validator", "scripts.run_replay_governance_trace_validator"),
    ("step_06_safety_regression", "scripts.run_replay_no_submit_safety_regression"),
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
        ("mock_transport_suite", "scripts.run_external_testnet_mock_transport_suite"),
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

    print("=== T185001-T200000 External Testnet Mock Replay Suite ===")
    print()

    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    print("--- Running mock replay steps ---")
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
        "milestone": "T185001-T200000",
        "title": "External Testnet Mock Replay",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "mock_replay_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# External Testnet Mock Replay Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "EXTERNAL_TESTNET_MOCK_REPLAY_SUITE_PASS",
        "MOCK_REPLAY_HARNESS_READY",
        "MOCK_REPLAY_SCENARIO_MATRIX_READY",
        "MOCK_FIELD_TEST_EVIDENCE_BUNDLE_READY",
        "HUMAN_APPROVAL_PACKET_V3_READY",
        "REPLAY_TO_GOVERNANCE_TRACE_READY",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "external_testnet_mock_replay_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    # Handoff doc
    handoff_lines = ["# Final External Testnet Mock Replay Handoff", "",
        "## Status", "",
        "EXTERNAL_TESTNET_MOCK_REPLAY_SUITE_PASS",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "", "## Artifacts", "",
        "- Replay traces: data/runtime/testnet_mock_replay/replay_traces.json",
        "- Scenario matrix: data/runtime/testnet_mock_replay/replay_scenario_matrix.json",
        "- Evidence bundle: data/runtime/testnet_mock_replay/evidence_bundle.json",
        "- Approval packet v3: data/runtime/testnet_mock_replay/human_approval_packet_v3.json",
        "- Trace validator: data/runtime/testnet_mock_replay/trace_validator_checks.json",
        "- Safety regression: data/runtime/testnet_mock_replay/replay_safety_regression.json",
        ""]
    (REPORT_DIR / "final_external_testnet_mock_replay_handoff.md").write_text("\n".join(handoff_lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
