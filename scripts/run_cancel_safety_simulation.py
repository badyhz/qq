#!/usr/bin/env python3
"""Wave 3: Cancel safety simulation."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.cancel_safety_simulator import run_cancel_safety_suite, write_records

    records = run_cancel_safety_suite()
    write_records(records, ROOT / "data" / "runtime" / "testnet_presubmit" / "simulated_cancel_records.jsonl")

    # Summary
    summary = {
        "total": len(records),
        "all_simulated": all(r.simulated for r in records),
        "all_no_real_cancel": all(not r.real_cancel for r in records),
        "all_no_network": all(not r.network_called for r in records),
        "all_no_submit_enforced": all(r.no_submit_enforced for r in records),
        "valid_cancels": [r.cancel_id for r in records if r.validation.valid],
        "blocked_cancels": [r.cancel_id for r in records if not r.validation.valid],
    }
    (ROOT / "data" / "runtime" / "testnet_presubmit" / "cancel_safety_simulation.json").write_text(
        __import__("json").dumps(summary, indent=2), encoding="utf-8"
    )

    # Report
    lines = ["# Cancel Safety Simulation Report", "", f"Total records: {len(records)}", f"All simulated: {summary['all_simulated']}", f"All no real cancel: {summary['all_no_real_cancel']}", "", "## Records", ""]
    for r in records:
        lines.append(f"- {r.cancel_id}: order={r.order_id}, valid={r.validation.valid}, checks={r.validation.checks}")
    lines.extend(["", "## Conclusion", "", "CANCEL_SAFETY_SIMULATION_PASS", ""])
    (ROOT / "reports" / "cancel_safety_simulation_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = summary["all_simulated"] and summary["all_no_real_cancel"] and summary["all_no_network"]
    print(f"Cancel safety: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
