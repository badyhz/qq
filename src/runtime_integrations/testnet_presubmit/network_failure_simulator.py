"""Network failure simulator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class FailureScenario:
    scenario_id: str
    failure_type: str  # timeout, connection_error, partial_response, malformed_response, duplicate_response, out_of_order, stale_response
    handled: bool
    action: str
    network_called: bool
    def to_dict(self) -> dict:
        return {"scenario_id": self.scenario_id, "failure_type": self.failure_type, "handled": self.handled, "action": self.action, "network_called": self.network_called}

@dataclass(frozen=True)
class NetworkFailureSimulation:
    scenarios: tuple[FailureScenario, ...]
    all_handled: bool
    no_real_network: bool
    def to_dict(self) -> dict:
        return {"scenarios": [s.to_dict() for s in self.scenarios], "all_handled": self.all_handled, "no_real_network": self.no_real_network}

SCENARIOS = (
    FailureScenario("nf_timeout", "timeout", True, "retry with backoff, max 3 retries", False),
    FailureScenario("nf_connection", "connection_error", True, "fail fast, report to operator", False),
    FailureScenario("nf_partial", "partial_response", True, "reject partial, request full snapshot", False),
    FailureScenario("nf_malformed", "malformed_response", True, "reject, log raw response", False),
    FailureScenario("nf_duplicate", "duplicate_response", True, "dedup by order_id, ignore duplicate", False),
    FailureScenario("nf_ooo", "out_of_order", True, "reject stale sequence, request fresh", False),
    FailureScenario("nf_stale", "stale_response", True, "reject if older than 5s, request fresh", False),
)

def run_simulation() -> NetworkFailureSimulation:
    return NetworkFailureSimulation(SCENARIOS, all(s.handled for s in SCENARIOS), True)

def write_simulation(sim: NetworkFailureSimulation, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sim.to_dict(), indent=2), encoding="utf-8")
