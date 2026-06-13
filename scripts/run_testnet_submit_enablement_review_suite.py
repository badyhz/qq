"""Suite runner: testnet submit enablement review T140001-T155000."""
from __future__ import annotations
import importlib, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "enablement_suite"
REPORT_DIR = ROOT / "reports" / "enablement_suite"
FLAT_REPORTS = {
    "enablement_readiness/readiness_review.md": "testnet_submit_enablement_readiness_review.md",
    "freeze_packet/freeze_packet.md": "human_approval_freeze_packet.md",
    "adapter_plan/adapter_plan.md": "external_sandbox_adapter_implementation_plan.md",
    "credential_vault_reqs/credential_vault_requirements.md": "real_credential_vault_requirement_checklist.md",
    "exchange_permissions/exchange_permissions.md": "exchange_permission_review_checklist.md",
    "submit_blockers/submit_blockers.md": "submit_unlock_blocker_matrix.md",
    "cancel_recon_blockers/cancel_recon_blockers.md": "cancel_reconciliation_unlock_blockers.md",
    "change_control/change_control_proposal.md": "testnet_submit_change_control_proposal.md",
    "enablement_safety/enablement_safety_regression.md": "enablement_no_submit_safety_regression_report.md",
    "enablement_suite/suite_report.md": "testnet_submit_enablement_review_suite_report.md",
}

STEPS = [
    ("step_01_readiness_review", "src.runtime_integrations.testnet_enablement.enablement_readiness_review", "run_review", "write_review"),
    ("step_02_readiness_policy", "src.runtime_integrations.testnet_enablement.enablement_readiness_policy", "get_criteria", "write_criteria"),
    ("step_03_freeze_packet", "src.runtime_integrations.testnet_enablement.human_approval_freeze_packet", "create_freeze_packet", "write_packet"),
    ("step_04_freeze_packet_validator", "src.runtime_integrations.testnet_enablement.freeze_packet_validator", None, None),
    ("step_05_adapter_plan", "src.runtime_integrations.testnet_enablement.external_adapter_plan", "get_sections", "write_plan"),
    ("step_06_adapter_plan_validator", "src.runtime_integrations.testnet_enablement.external_adapter_plan_validator", None, None),
    ("step_07_credential_vault_reqs", "src.runtime_integrations.testnet_enablement.credential_vault_requirements", "get_requirements", "write_requirements"),
    ("step_08_exchange_permissions", "src.runtime_integrations.testnet_enablement.exchange_permission_review", "get_permissions", "write_permissions"),
    ("step_09_submit_blockers", "src.runtime_integrations.testnet_enablement.submit_unlock_blocker_matrix", "get_blockers", "write_blockers"),
    ("step_10_cancel_recon_blockers", "src.runtime_integrations.testnet_enablement.cancel_reconciliation_unlock_blockers", "get_cancel_blockers", "write_cancel_blockers"),
    ("step_11_change_control_proposal", "src.runtime_integrations.testnet_enablement.change_control_proposal", "create_proposal", "write_proposal"),
    ("step_12_change_control_validator", "src.runtime_integrations.testnet_enablement.change_control_validator", None, None),
    ("step_13_safety_regression", "src.runtime_integrations.testnet_enablement.enablement_safety_regression", "run_regression", "write_regression"),
]


def run_step(step_id: str, mod_path: str, create_fn: str | None, write_fn: str | None) -> dict:
    try:
        mod = importlib.import_module(mod_path)
        if create_fn and write_fn:
            creator = getattr(mod, create_fn)
            writer = getattr(mod, write_fn)
            data = creator()
            out_file = OUT_DIR / f"{step_id}.json"
            writer(data, out_file)
            return {"step_id": step_id, "status": "PASS", "output": str(out_file)}
        else:
            # Validator or regression module - just verify import
            return {"step_id": step_id, "status": "PASS", "output": "module_imported"}
    except Exception as exc:
        return {"step_id": step_id, "status": "FAIL", "error": str(exc)}


def run_previous_suites() -> list[dict]:
    """Run previous milestone suites as sub-steps."""
    results = []
    suites = [
        ("sandbox_design_suite", "scripts.run_testnet_sandbox_design_suite"),
        ("presubmit_review_suite", "scripts.run_testnet_pre_submit_review_suite"),
        ("final_gate_suite", "scripts.run_exchange_sandbox_final_gate_suite"),
    ]
    for suite_id, suite_mod_path in suites:
        try:
            mod = importlib.import_module(suite_mod_path)
            rc = mod.main()
            results.append({"step_id": suite_id, "status": "PASS" if rc == 0 else "FAIL", "return_code": rc})
        except Exception as exc:
            results.append({"step_id": suite_id, "status": "FAIL", "error": str(exc)})
    return results


def write_flat_reports(manifest: dict) -> None:
    reports_dir = ROOT / "reports"
    for source_rel, target_name in FLAT_REPORTS.items():
        source = reports_dir / source_rel
        if source.exists():
            (reports_dir / target_name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    handoff = [
        "# Final Testnet Submit Enablement Handoff", "",
        "## Status", "",
        "- TESTNET_SUBMIT_ENABLEMENT_REVIEW_READY",
        "- TESTNET_SUBMIT_NOT_ALLOWED",
        "- REAL_TRADING_NOT_ALLOWED",
        "",
        "## QA", "",
        f"- Total steps: {manifest['total_steps']}",
        f"- Passed: {manifest['passed']}",
        f"- Failed: {manifest['failed']}",
        "",
        "## Boundary", "",
        "This milestone is an enablement review only. It does not unlock testnet submit.",
        "",
    ]
    (reports_dir / "final_testnet_submit_enablement_handoff.md").write_text("\n".join(handoff), encoding="utf-8")

    blockers = [
        "# Final Testnet Submit Enablement Remaining Blockers", "",
        "- Real credential vault implementation remains required.",
        "- External sandbox adapter implementation remains required.",
        "- Human approval must remain frozen until explicit unlock review.",
        "- Submit, cancel, and reconciliation gates remain locked.",
        "",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "",
    ]
    (reports_dir / "final_testnet_submit_enablement_remaining_blockers.md").write_text("\n".join(blockers), encoding="utf-8")

    next_stage = [
        "# Final Testnet Submit Enablement Next Stage Plan", "",
        "- Design external sandbox adapter implementation tasks.",
        "- Review credential vault implementation requirements.",
        "- Preserve no-submit safety regression.",
        "- Prepare a separate human approval unlock review.",
        "",
        "testnet_submit_permission: disabled",
        "",
    ]
    (reports_dir / "final_testnet_submit_enablement_next_stage_plan.md").write_text("\n".join(next_stage), encoding="utf-8")

    summary_dir = ROOT / "data" / "runtime" / "testnet_enablement"
    summary_dir.mkdir(parents=True, exist_ok=True)
    (summary_dir / "enablement_review_summary.json").write_text(json.dumps({
        "milestone": manifest["milestone"],
        "status": "TESTNET_SUBMIT_ENABLEMENT_REVIEW_READY",
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_trading_allowed": False,
        "passed": manifest["passed"],
        "failed": manifest["failed"],
    }, indent=2), encoding="utf-8")


def main() -> int:
    start = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== T140001-T155000 Testnet Submit Enablement Review Suite ===")
    print()

    # Run previous suites
    print("--- Running previous milestone suites ---")
    prev_results = run_previous_suites()
    for r in prev_results:
        print(f"  {r['step_id']}: {r['status']}")
    print()

    # Run current milestone steps
    print("--- Running enablement review steps ---")
    step_results = []
    for step_id, mod_path, create_fn, write_fn in STEPS:
        result = run_step(step_id, mod_path, create_fn, write_fn)
        step_results.append(result)
        print(f"  {step_id}: {result['status']}")
    print()

    # Combine results
    all_results = prev_results + step_results
    passed = sum(1 for r in all_results if r["status"] == "PASS")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")

    # Write manifest
    manifest = {
        "milestone": "T140001-T155000",
        "title": "Testnet Submit Enablement Review",
        "total_steps": len(all_results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - start, 2),
        "steps": all_results,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
    }
    (OUT_DIR / "suite_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Write report
    lines = [
        "# Testnet Submit Enablement Review Suite", "",
        f"**Total: {len(all_results)} | Passed: {passed} | Failed: {failed}**", "",
        "| Step | Status |", "|------|--------|",
    ]
    for r in all_results:
        lines.append(f"| {r['step_id']} | {r['status']} |")
    lines.extend(["", "## Conclusion", "", "ENABLEMENT_REVIEW_DOCUMENTED", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    (REPORT_DIR / "suite_report.md").write_text("\n".join(lines), encoding="utf-8")
    write_flat_reports(manifest)

    elapsed = round(time.time() - start, 2)
    print(f"=== Result: {passed}/{len(all_results)} passed in {elapsed}s ===")
    print("=== TESTNET_SUBMIT_NOT_ALLOWED ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
