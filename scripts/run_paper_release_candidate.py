"""Release candidate runner — one-click full RC validation. No network."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.release_manifest import generate_manifest, manifest_ready, manifest_to_markdown
from core.paper_trading.artifact_validator import validate_artifacts, has_errors

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")

RUNNERS = [
    ("compileall", [sys.executable, "-m", "compileall", "-q", "core", "scripts", "tests"]),
    ("dry_run", [sys.executable, "scripts/run_paper_trading_decision_engine_dry.py"]),
    ("multi_fixture", [sys.executable, "scripts/run_paper_multi_fixture_replay.py"]),
    ("parameter_sweep", [sys.executable, "scripts/run_paper_parameter_sweep.py"]),
    ("ops_report", [sys.executable, "scripts/run_paper_trading_ops_report.py"]),
    ("runtime", [sys.executable, "scripts/run_paper_runtime.py"]),
    ("daily_ops", [sys.executable, "scripts/run_paper_daily_ops.py"]),
    ("operator_review", [sys.executable, "scripts/run_paper_operator_review.py"]),
    ("acceptance_suite", [sys.executable, "scripts/run_paper_trading_acceptance_suite.py"]),
]


def run_step(name: str, cmd: list, timeout: int = 600) -> dict:
    start = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT)
        return {"name": name, "passed": r.returncode == 0, "elapsed_s": round(time.time() - start, 2),
                "returncode": r.returncode, "output_tail": (r.stdout + r.stderr).strip()[-200:]}
    except subprocess.TimeoutExpired:
        return {"name": name, "passed": False, "elapsed_s": timeout, "returncode": -1, "output_tail": "TIMEOUT"}
    except Exception as e:
        return {"name": name, "passed": False, "elapsed_s": 0, "returncode": -1, "output_tail": str(e)[:200]}


def main():
    print("=== Paper Trading Release Candidate ===\n")
    os.makedirs(REPORT_DIR, exist_ok=True)
    total_start = time.time()

    # Run all steps
    results = []
    for name, cmd in RUNNERS:
        print(f"Running: {name} ...", flush=True)
        r = run_step(name, cmd)
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['elapsed_s']}s")
        results.append(r)

    # Generate manifest
    print("Generating manifest ...", flush=True)
    manifest = generate_manifest()
    ready = manifest_ready(manifest)
    print(f"  RC Ready: {ready}")

    # Validate artifacts
    print("Validating artifacts ...", flush=True)
    issues = validate_artifacts(REPORT_DIR)
    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARNING"]
    print(f"  Errors: {len(errors)}, Warnings: {len(warnings)}")

    # Dashboard index
    print("Generating dashboard index ...", flush=True)
    try:
        from core.paper_trading.dashboard_index import write_index
        write_index(REPORT_DIR)
    except Exception as e:
        print(f"  Index failed: {e}")

    total_elapsed = round(time.time() - total_start, 2)
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    # Summary
    print(f"\n=== RC Summary ===")
    print(f"Runners: {passed}/{len(results)} passed")
    print(f"RC Ready: {ready}")
    print(f"Artifact errors: {len(errors)}")
    print(f"Total time: {total_elapsed}s")
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['name']} ({r['elapsed_s']}s)")

    # JSON output
    rc_data = {
        "version": manifest["version"],
        "generated_at": manifest["generated_at"],
        "paper_only": True,
        "rc_ready": ready,
        "total_elapsed_s": total_elapsed,
        "runners_passed": passed,
        "runners_failed": failed,
        "steps": results,
        "manifest": {
            "modules_found": manifest["modules"]["found"],
            "modules_expected": manifest["modules"]["expected"],
            "scripts_found": manifest["scripts"]["found"],
            "scripts_expected": manifest["scripts"]["expected"],
        },
        "artifact_errors": len(errors),
        "artifact_warnings": len(warnings),
        "safety_flags": manifest["safety_flags"],
        "known_limits": manifest["known_limits"],
        "next_phase_blockers": manifest["next_phase_blockers"],
    }
    json_path = os.path.join(REPORT_DIR, "paper_trading_release_candidate.json")
    with open(json_path, "w") as f:
        json.dump(rc_data, f, indent=2)
    print(f"\nJSON: {json_path}")

    # Markdown output
    md_path = os.path.join(REPORT_DIR, "paper_trading_release_candidate.md")
    with open(md_path, "w") as f:
        f.write("# Paper Trading Release Candidate Report\n\n")
        f.write(f"**Version:** {manifest['version']}\n")
        f.write(f"**Date:** {manifest['generated_at']}\n")
        f.write(f"**Mode:** paper-only / local / no network\n\n")
        f.write(f"## RC Ready: {'YES' if ready else 'NO'}\n\n")
        f.write("## Runners\n\n| Step | Status | Time |\n|------|--------|------|\n")
        for r in results:
            mark = "PASS" if r["passed"] else "FAIL"
            f.write(f"| {r['name']} | {mark} | {r['elapsed_s']}s |\n")
        f.write(f"\n**Total:** {passed}/{len(results)} passed in {total_elapsed}s\n\n")
        f.write("## Manifest\n\n")
        f.write(f"- Modules: {manifest['modules']['found']}/{manifest['modules']['expected']}\n")
        f.write(f"- Scripts: {manifest['scripts']['found']}/{manifest['scripts']['expected']}\n")
        f.write(f"- Artifacts: {len(errors)} errors, {len(warnings)} warnings\n\n")
        f.write("## Safety Flags\n\n")
        for flag in manifest["safety_flags"]:
            f.write(f"- {flag}")
        f.write("\n\n## Known Limits\n\n")
        for lim in manifest["known_limits"]:
            f.write(f"- {lim}")
        f.write("\n\n## Next Phase Blockers\n\n")
        for blk in manifest["next_phase_blockers"]:
            f.write(f"- {blk}")
        f.write("\n")
    print(f"Markdown: {md_path}")

    if failed > 0 or not ready:
        print(f"\nStatus: PAPER_RC_INCOMPLETE ({failed} failures, ready={ready})")
        return 1
    print(f"\nStatus: PAPER_RELEASE_CANDIDATE_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
