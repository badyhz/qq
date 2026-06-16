"""Daily ops runner — one-click all paper runners + dashboard index. No network."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")

RUNNERS = [
    ("dry_run", "scripts/run_paper_trading_decision_engine_dry.py"),
    ("multi_fixture", "scripts/run_paper_multi_fixture_replay.py"),
    ("parameter_sweep", "scripts/run_paper_parameter_sweep.py"),
    ("ops_report", "scripts/run_paper_trading_ops_report.py"),
    ("runtime", "scripts/run_paper_runtime.py"),
    ("operator_review", "scripts/run_paper_operator_review.py"),
]


def run_script(name: str, script: str, timeout: int = 300) -> dict:
    """Run a script and return status info."""
    start = time.time()
    try:
        r = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True,
            timeout=timeout, cwd=REPO_ROOT,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "name": name,
            "script": script,
            "returncode": r.returncode,
            "elapsed_s": elapsed,
            "passed": r.returncode == 0,
            "output_tail": (r.stdout + r.stderr).strip()[-300:],
        }
    except subprocess.TimeoutExpired:
        return {
            "name": name, "script": script,
            "returncode": -1, "elapsed_s": timeout,
            "passed": False, "output_tail": "TIMEOUT",
        }
    except Exception as e:
        return {
            "name": name, "script": script,
            "returncode": -1, "elapsed_s": 0,
            "passed": False, "output_tail": str(e)[:300],
        }


def main():
    print("=== Paper Trading Daily Ops ===\n")
    os.makedirs(REPORT_DIR, exist_ok=True)

    results = []
    total_start = time.time()

    for name, script in RUNNERS:
        print(f"Running: {name} ...", flush=True)
        result = run_script(name, script)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{status}] {result['elapsed_s']}s")
        results.append(result)

    # Generate dashboard index
    print("Generating dashboard index ...", flush=True)
    try:
        sys.path.insert(0, REPO_ROOT)
        from core.paper_trading.dashboard_index import write_index
        index_path = write_index(REPORT_DIR)
        print(f"  Index: {index_path}")
    except Exception as e:
        print(f"  Index failed: {e}")

    total_elapsed = round(time.time() - total_start, 2)
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    # Summary
    print(f"\n=== Summary ===")
    print(f"Passed: {passed}/{len(results)}")
    print(f"Total time: {total_elapsed}s")
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['name']} ({r['elapsed_s']}s)")

    # Load operator review results if available
    operator_review = {}
    review_json_path = os.path.join(REPORT_DIR, "paper_trading_operator_review.json")
    if os.path.isfile(review_json_path):
        try:
            with open(review_json_path) as f:
                operator_review = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # JSON output
    summary = {
        "date": time.strftime("%Y-%m-%d"),
        "total_elapsed_s": total_elapsed,
        "passed": passed,
        "failed": failed,
        "runners": results,
        "operator_review": operator_review,
    }
    json_path = os.path.join(REPORT_DIR, "paper_trading_daily_ops.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nJSON: {json_path}")

    # Markdown output
    md_path = os.path.join(REPORT_DIR, "paper_trading_daily_ops.md")
    with open(md_path, "w") as f:
        f.write("# Paper Trading Daily Ops Report\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d')}\n")
        f.write(f"**Mode:** paper-only / local / no network\n\n")
        f.write("## Results\n\n")
        f.write("| Runner | Status | Time |\n|--------|--------|------|\n")
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            f.write(f"| {r['name']} | {status} | {r['elapsed_s']}s |\n")
        f.write(f"\n**Total:** {passed}/{len(results)} passed in {total_elapsed}s\n\n")

        # Review queue summary
        if operator_review:
            f.write("## Operator Review\n\n")
            qs = operator_review.get("queue_summary", {})
            rs = operator_review.get("ranked_summary", {})
            f.write(f"- Queue total: {qs.get('total', 0)}\n")
            f.write(f"- Pending: {qs.get('PENDING_REVIEW', 0)}\n")
            f.write(f"- HIGH: {rs.get('high', 0)} | MEDIUM: {rs.get('medium', 0)} | LOW: {rs.get('low', 0)} | REJECT: {rs.get('reject', 0)}\n")
            f.write(f"- Score: {operator_review.get('score', 0):.1f} | Rating: {operator_review.get('rating', 'N/A')}\n\n")

        f.write("## Safety\n\n- NO real orders\n- NO network\n- NO testnet/live\n- Paper only\n")
    print(f"Markdown: {md_path}")

    if failed > 0:
        print(f"\nStatus: PAPER_DAILY_OPS_FAIL ({failed} failures)")
        return 1
    print(f"\nStatus: PAPER_DAILY_OPS_COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
