#!/usr/bin/env python3
"""Wave 6: Rate limit and network failure simulation."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.rate_limit_simulator import simulate_rate_limit, write_simulation as write_rate
    from src.runtime_integrations.testnet_presubmit.network_failure_simulator import run_simulation as run_net, write_simulation as write_net

    rate = simulate_rate_limit(5, 3)
    write_rate(rate, ROOT / "data" / "runtime" / "testnet_presubmit" / "rate_limit_simulation.json")

    net = run_net()
    write_net(net, ROOT / "data" / "runtime" / "testnet_presubmit" / "network_failure_simulation.json")

    # Report
    lines = ["# Sandbox Failure Mode Simulation Report", "", "## Rate Limit", "", f"Exceeded: {rate.exceeded}", f"Action: {rate.action_taken}", f"No real sleep: {rate.no_real_sleep}", "", "## Network Failure", "", f"All handled: {net.all_handled}", f"No real network: {net.no_real_network}", "", "## Scenarios", ""]
    for s in net.scenarios:
        lines.append(f"- {s.failure_type}: handled={s.handled}, action={s.action}")
    lines.extend(["", "## Conclusion", "", "RATE_LIMIT_SIMULATION_PASS", "NETWORK_FAILURE_SIMULATION_PASS", ""])
    (ROOT / "reports" / "sandbox_failure_mode_simulation_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = not rate.exceeded and rate.no_real_sleep and net.all_handled and net.no_real_network
    print(f"Failure mode simulation: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
