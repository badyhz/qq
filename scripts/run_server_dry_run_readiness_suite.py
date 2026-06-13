#!/usr/bin/env python3
"""T80001-T95000 — Server Dry-Run Readiness Suite Runner."""
import json, sys, pathlib, tempfile
from datetime import datetime, timezone
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    now = datetime.now(timezone.utc).isoformat()
    steps = {}
    errors = []

    # 1. Artifact hygiene policy
    try:
        from src.runtime_integrations.hygiene.runtime_artifact_policy import get_policies, write_policy_json, render_policy_markdown
        policies = get_policies()
        write_policy_json(policies, ROOT / "data" / "runtime" / "hygiene" / "artifact_policy.json")
        (ROOT / "reports" / "runtime_artifact_policy_report.md").write_text(render_policy_markdown(), encoding="utf-8")
        steps["artifact_hygiene"] = "PASS"
    except Exception as e:
        steps["artifact_hygiene"] = "FAIL"
        errors.append(f"artifact_hygiene: {e}")

    # 2. Git pollution check
    try:
        from src.runtime_integrations.hygiene.git_pollution_checker import check_pollution, write_check
        items = check_pollution(ROOT)
        write_check(items, ROOT / "data" / "runtime" / "hygiene" / "git_pollution.json")
        has_block = any(i.severity == "BLOCK" for i in items)
        steps["git_pollution"] = "FAIL" if has_block else "PASS"
    except Exception as e:
        steps["git_pollution"] = "FAIL"
        errors.append(f"git_pollution: {e}")

    # 3. Output router
    try:
        from src.runtime_integrations.hygiene.output_router import route_output
        iso_dir = route_output(ROOT / "data" / "runtime" / "e2e", f"readiness_{now[:10]}")
        routing = {"run_dir": str(iso_dir), "created": now}
        (ROOT / "data" / "runtime" / "hygiene" / "routing_manifest.json").write_text(json.dumps(routing, indent=2), encoding="utf-8")
        steps["output_router"] = "PASS"
    except Exception as e:
        steps["output_router"] = "FAIL"
        errors.append(f"output_router: {e}")

    # 4. Scheduled E2E simulation
    try:
        from src.runtime_integrations.scheduler.scheduled_e2e_simulator import simulate_scheduled_runs, write_runs
        runs = simulate_scheduled_runs(3)
        write_runs(runs, ROOT / "data" / "runtime" / "scheduler" / "scheduled_runs.jsonl")
        all_ok = all(r.status == "COMPLETED" for r in runs)
        steps["scheduled_e2e"] = "PASS" if all_ok else "FAIL"
        # Write summary manifest
        manifest = {"run_count": len(runs), "statuses": [r.status for r in runs], "overall": "SCHEDULE_PASS" if all_ok else "SCHEDULE_FAIL"}
        (ROOT / "data" / "runtime" / "scheduler" / "schedule_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except Exception as e:
        steps["scheduled_e2e"] = "FAIL"
        errors.append(f"scheduled_e2e: {e}")

    # 5. Server environment check
    try:
        from src.runtime_integrations.server.server_environment_checker import check_environment, write_checks as write_env_checks
        env_checks = check_environment(ROOT)
        write_env_checks(env_checks, ROOT / "data" / "runtime" / "server" / "environment_check.json")
        steps["server_environment"] = "PASS" if all(c.passed for c in env_checks) else "WARN"
    except Exception as e:
        steps["server_environment"] = "FAIL"
        errors.append(f"server_environment: {e}")

    # 6. Systemd template validation
    try:
        from src.runtime_integrations.server.systemd_template_validator import validate_all_templates, write_validations
        template_vals = validate_all_templates(ROOT / "deployment" / "runtime_dry_run")
        write_validations(template_vals, ROOT / "data" / "runtime" / "server" / "systemd_validation.json")
        steps["systemd_templates"] = "PASS" if all(v.valid for v in template_vals) else "FAIL"
    except Exception as e:
        steps["systemd_templates"] = "FAIL"
        errors.append(f"systemd_templates: {e}")

    # 7. Log rotation policy
    try:
        from src.runtime_integrations.server.log_rotation_policy import get_rules, write_rules, render_log_rotation_markdown
        rules = get_rules()
        write_rules(rules, ROOT / "data" / "runtime" / "hygiene" / "retention_rules.json")
        (ROOT / "reports" / "log_rotation_report.md").write_text(render_log_rotation_markdown(), encoding="utf-8")
        steps["log_rotation"] = "PASS"
    except Exception as e:
        steps["log_rotation"] = "FAIL"
        errors.append(f"log_rotation: {e}")

    # 8. Feishu payload validation
    try:
        from src.runtime_integrations.alerts.feishu_payload_validator import validate_payloads_file, write_validations as write_feishu_validations
        feishu_vals = validate_payloads_file(ROOT / "data" / "runtime" / "alerts" / "feishu_dry_run_payloads.jsonl")
        write_feishu_validations(feishu_vals, ROOT / "data" / "runtime" / "alerts" / "feishu_payload_validation.json")
        steps["feishu_payload"] = "PASS" if all(v.valid for v in feishu_vals) else "FAIL"
    except Exception as e:
        steps["feishu_payload"] = "FAIL"
        errors.append(f"feishu_payload: {e}")

    # 9. Server no-submit regression
    try:
        from src.runtime_integrations.server.server_no_submit_regression import run_server_safety_checks, write_checks as write_server_checks
        server_checks = run_server_safety_checks(ROOT)
        write_server_checks(server_checks, ROOT / "data" / "runtime" / "server" / "server_safety.json")
        steps["server_no_submit"] = "PASS" if all(c.passed for c in server_checks) else "FAIL"
    except Exception as e:
        steps["server_no_submit"] = "FAIL"
        errors.append(f"server_no_submit: {e}")

    # 10. Testnet sandbox gap analysis
    try:
        from src.runtime_integrations.testnet_sim.testnet_sandbox_gap_analyzer import get_gaps, write_gaps, render_gap_report_markdown, render_approval_checklist_markdown
        gaps = get_gaps()
        write_gaps(gaps, ROOT / "data" / "runtime" / "testnet_sim" / "sandbox_gaps.json")
        (ROOT / "reports" / "testnet_sandbox_gap_report.md").write_text(render_gap_report_markdown(), encoding="utf-8")
        (ROOT / "reports" / "testnet_approval_checklist.md").write_text(render_approval_checklist_markdown(), encoding="utf-8")
        steps["testnet_gaps"] = "PASS"
    except Exception as e:
        steps["testnet_gaps"] = "FAIL"
        errors.append(f"testnet_gaps: {e}")

    # 11. Feishu review packet
    try:
        from src.runtime_integrations.alerts.feishu_review_packet import build_review_packet, write_packet
        packet = build_review_packet(ROOT / "data" / "runtime" / "e2e")
        write_packet(packet, ROOT / "data" / "runtime" / "alerts" / "feishu_review_packet.json")
        steps["review_packet"] = "PASS"
    except Exception as e:
        steps["review_packet"] = "FAIL"
        errors.append(f"review_packet: {e}")

    # Final status
    all_pass = all(v in ("PASS", "WARN") for v in steps.values())
    final_status = "SERVER_DRY_RUN_READINESS_PASS" if all_pass else "SERVER_DRY_RUN_READINESS_BLOCKED"

    # Write manifest
    manifest = {
        "manifest_id": f"server_{now.replace(':', '').replace('-', '')[:20]}",
        "timestamp": now,
        "steps": steps,
        "errors": errors,
        "status": final_status,
    }
    out_dir = ROOT / "data" / "runtime" / "server_readiness"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "readiness_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Write report
    lines = [
        "# Server Dry-Run Readiness Suite Report",
        "",
        f"**Status:** {final_status}",
        "",
        "## Steps",
        "",
    ]
    for k, v in steps.items():
        lines.append(f"- {k}: {v}")
    if errors:
        lines.append("")
        lines.append("## Errors")
        for e in errors:
            lines.append(f"- {e}")
    lines.append("")
    (ROOT / "reports" / "server_dry_run_readiness_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Server Readiness: {final_status}")
    for k, v in steps.items():
        print(f"  {k}: {v}")
    if errors:
        print(f"Errors: {len(errors)}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
