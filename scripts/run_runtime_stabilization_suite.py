#!/usr/bin/env python3
"""T77001 — Runtime Stabilization Suite Runner."""
import json, sys, pathlib
from datetime import datetime, timezone
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    now = datetime.now(timezone.utc).isoformat()
    steps = {}
    errors = []

    # 1. Baseline E2E
    try:
        from src.runtime_integrations.e2e.system_dry_run_e2e import run_e2e
        e2e = run_e2e(ROOT / "data", ROOT / "reports")
        steps["e2e"] = e2e.get("status", "UNKNOWN")
        if e2e.get("errors"):
            errors.extend(e2e["errors"])
    except Exception as e:
        steps["e2e"] = "FAIL"
        errors.append(f"e2e: {e}")

    # 2. Replay harness
    try:
        from src.runtime_integrations.replay.replay_harness import run_replay, write_manifest, write_report
        manifest = run_replay(3, ROOT / "data", ROOT / "reports")
        write_manifest(manifest, ROOT / "data" / "runtime" / "replay" / "replay_manifest.json")
        write_report(manifest, ROOT / "reports" / "runtime_replay_harness_report.md")
        steps["replay"] = "PASS" if manifest.all_passed else "FAIL"
    except Exception as e:
        steps["replay"] = "FAIL"
        errors.append(f"replay: {e}")

    # 3. Scenario suite
    try:
        from src.runtime_integrations.scenarios.scenario_runner import run_scenario_suite, write_results, write_report as write_scenario_report
        results = run_scenario_suite(ROOT / "tests" / "fixtures" / "runtime_scenarios")
        write_results(results, ROOT / "data" / "runtime" / "scenarios" / "scenario_results.jsonl")
        write_scenario_report(results, ROOT / "reports" / "runtime_scenario_suite_report.md")
        steps["scenarios"] = "PASS" if all(r.status in ("PASS", "PASS_WITH_WARNINGS", "EXPECTED_BLOCKED") for r in results) else "FAIL"
    except Exception as e:
        steps["scenarios"] = "FAIL"
        errors.append(f"scenarios: {e}")

    # 4. Alert dedup replay
    try:
        from src.runtime_integrations.alerts.dedup_store import DedupStore
        from src.runtime_integrations.alerts.alert_replay import replay_alerts, write_report as write_dedup_report
        store = DedupStore(ROOT / "data" / "runtime" / "alerts" / "dedup_store.json")
        dedup_report = replay_alerts(ROOT / "data" / "runtime" / "alerts" / "alerts.jsonl", store)
        write_dedup_report(dedup_report, ROOT / "data" / "runtime" / "alerts" / "dedup_replay_report.json")
        steps["alert_dedup"] = "PASS"
    except Exception as e:
        steps["alert_dedup"] = "FAIL"
        errors.append(f"alert_dedup: {e}")

    # 5. Artifact integrity
    try:
        from src.runtime_integrations.artifacts.artifact_manifest import scan_artifacts, write_manifest as write_art_manifest, write_hashes
        from src.runtime_integrations.artifacts.artifact_validator import validate
        from src.runtime_integrations.artifacts.artifact_retention_policy import write_policy
        entries = scan_artifacts(ROOT)
        write_art_manifest(entries, ROOT / "data" / "runtime" / "artifacts" / "artifact_manifest.jsonl")
        write_hashes(entries, ROOT / "data" / "runtime" / "artifacts" / "artifact_hashes.json")
        write_policy(ROOT / "reports" / "runtime_artifact_retention_policy.md")
        validation = validate(entries)
        steps["artifact_integrity"] = "PASS" if validation.all_valid else "FAIL"
    except Exception as e:
        steps["artifact_integrity"] = "FAIL"
        errors.append(f"artifact_integrity: {e}")

    # 6. Dashboard regression
    try:
        from src.runtime_integrations.operator.dashboard_regression import check_dashboard, write_regression
        checks = check_dashboard(ROOT / "data" / "runtime" / "operator" / "system_state.json", ROOT / "reports" / "operator_dashboard.html")
        write_regression(checks, ROOT / "data" / "runtime" / "operator" / "dashboard_regression.json")
        steps["dashboard_regression"] = "PASS" if all(c.passed for c in checks) else "FAIL"
    except Exception as e:
        steps["dashboard_regression"] = "FAIL"
        errors.append(f"dashboard_regression: {e}")

    # 7. Observability
    try:
        from src.runtime_integrations.observability.runtime_metrics import collect_metrics, write_metrics
        from src.runtime_integrations.observability.runtime_health import evaluate_health, write_health
        metrics = collect_metrics(ROOT / "data", ROOT / "reports")
        write_metrics(metrics, ROOT / "data" / "runtime" / "observability" / "runtime_metrics.json")
        health = evaluate_health(metrics)
        write_health(health, ROOT / "data" / "runtime" / "observability" / "runtime_health.json")
        steps["observability"] = "PASS" if health.status == "OK" else "WARN"
    except Exception as e:
        steps["observability"] = "FAIL"
        errors.append(f"observability: {e}")

    # 8. No-submit regression
    try:
        from src.runtime_integrations.safety.no_submit_regression import run_safety_checks, write_checks
        safety_checks = run_safety_checks(ROOT / "data", ROOT / "reports")
        write_checks(safety_checks, ROOT / "data" / "runtime" / "safety" / "no_submit_regression.json")
        steps["no_submit_regression"] = "PASS" if all(c.passed for c in safety_checks) else "FAIL"
    except Exception as e:
        steps["no_submit_regression"] = "FAIL"
        errors.append(f"no_submit_regression: {e}")

    # 9. Server readiness
    try:
        server_files = [
            ROOT / "deployment" / "runtime_dry_run" / "README.md",
            ROOT / "deployment" / "runtime_dry_run" / "env.example",
            ROOT / "deployment" / "runtime_dry_run" / "safety_checklist.md",
        ]
        all_exist = all(f.exists() for f in server_files)
        steps["server_readiness"] = "PASS" if all_exist else "FAIL"
    except Exception as e:
        steps["server_readiness"] = "FAIL"
        errors.append(f"server_readiness: {e}")

    # Final status
    all_pass = all(v in ("PASS", "WARN", "SYSTEM_DRY_RUN_E2E_PASS") for v in steps.values())
    final_status = "RUNTIME_STABILIZATION_SUITE_PASS" if all_pass else "RUNTIME_STABILIZATION_SUITE_BLOCKED"

    # Write manifest
    manifest = {
        "manifest_id": f"stab_{now.replace(':', '').replace('-', '')[:20]}",
        "timestamp": now,
        "steps": steps,
        "errors": errors,
        "status": final_status,
    }
    (ROOT / "data" / "runtime" / "stabilization" / "stabilization_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    # Write report
    lines = [
        "# Runtime Stabilization Suite Report",
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
    (ROOT / "reports" / "runtime_stabilization_suite_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Stabilization: {final_status}")
    for k, v in steps.items():
        print(f"  {k}: {v}")
    if errors:
        print(f"Errors: {len(errors)}")


if __name__ == "__main__":
    main()
