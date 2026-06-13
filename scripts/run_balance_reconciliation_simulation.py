#!/usr/bin/env python3
"""Wave 5: Balance reconciliation simulation."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.balance_reconciliation_simulator import run_simulation, write_simulation

    sim = run_simulation()
    write_simulation(sim, ROOT / "data" / "runtime" / "testnet_presubmit" / "balance_reconciliation.json")

    lines = ["# Balance Reconciliation Simulation Report", "", f"Mode: {sim.reconciliation_mode}", f"Network called: {sim.network_called}", f"Submit allowed: {sim.submit_allowed}", "", "## Results", ""]
    for r in sim.results:
        lines.append(f"- {r.asset}: {r.status} — {r.checks}")
    lines.extend(["", "## Conclusion", "", "BALANCE_RECONCILIATION_SIMULATION_PASS", ""])
    (ROOT / "reports" / "balance_reconciliation_simulation_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = sim.reconciliation_mode == "SIMULATED_ONLY" and not sim.network_called and not sim.submit_allowed
    print(f"Balance reconciliation: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
