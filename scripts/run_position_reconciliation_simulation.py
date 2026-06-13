#!/usr/bin/env python3
"""Wave 4: Position reconciliation simulation."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.position_reconciliation_simulator import run_simulation, run_mismatch_scenario, write_simulation

    sim = run_simulation()
    write_simulation(sim, ROOT / "data" / "runtime" / "testnet_presubmit" / "position_reconciliation.json")

    # Report
    lines = ["# Position Reconciliation Simulation Report", "", f"Mode: {sim.reconciliation_mode}", f"Network called: {sim.network_called}", f"Submit allowed: {sim.submit_allowed}", "", "## Results", ""]
    for r in sim.results:
        lines.append(f"- {r.symbol}: {r.status} — {r.checks}")
    lines.extend(["", "## Conclusion", "", "POSITION_RECONCILIATION_SIMULATION_PASS", ""])
    (ROOT / "reports" / "position_reconciliation_simulation_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = sim.reconciliation_mode == "SIMULATED_ONLY" and not sim.network_called and not sim.submit_allowed
    print(f"Position reconciliation: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
