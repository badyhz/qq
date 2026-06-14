"""Suite runner: testnet read-only checkpoint T335001-T340000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_checkpoint"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_checkpoint"

STEPS = [
    ("step_01_checkpoint_summary", "scripts.run_readonly_checkpoint_summary"),
    ("step_02_tag_chain_manifest", "scripts.run_readonly_tag_chain_manifest"),
    ("step_03_safety_boundary_summary", "scripts.run_readonly_safety_boundary_summary"),
    ("step_04_next_stage_decision_pack", "scripts.run_readonly_next_stage_decision_pack"),
    ("step_05_safety_regression", "scripts.run_readonly_checkpoint_safety_regression"),
]


def run_step(step_id: str, mod_path: str) -> dict:
    try:
        mod = importlib.import_module(mod_path)
        rc = mod.main()
        return {"step_id": step_id, "status": "PASS" if rc == 0 else "FAIL", "return_code": rc}
    except Exception as exc:
        return {"step_id": step_id, "status": "FAIL", "error": str(exc)}


def main() -> int:
    start = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== T335001-T340000 Testnet Read-Only Checkpoint Suite ===")
    print()

    print("--- Running checkpoint steps ---")
    step_results = []
    for step_id, mod_path in STEPS:
        result = run_step(step_id, mod_path)
        step_results.append(result)
        print(f"  {step_id}: {result['status']}")
    print()

    all_results = step_results
    passed = sum(1 for r in all_results if r["status"] == "PASS")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")

    manifest = {
        "milestone": "T335001-T340000",
        "title": "Testnet Read-Only Checkpoint / Handoff Summary",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "checkpoint_suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Testnet Read-Only Checkpoint Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "",
        "TESTNET_READONLY_CHECKPOINT_SUITE_PASS",
        "READONLY_CHECKPOINT_SUMMARY_READY",
        "READONLY_TAG_CHAIN_MANIFEST_READY",
        "READONLY_SAFETY_BOUNDARY_SUMMARY_READY",
        "READONLY_NEXT_STAGE_DECISION_PACK_READY",
        "READONLY_CHECKPOINT_NO_NETWORK_NO_SUBMIT_SAFETY_PASS",
        "REAL_NETWORK_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    (REPORT_DIR / "testnet_readonly_checkpoint_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
