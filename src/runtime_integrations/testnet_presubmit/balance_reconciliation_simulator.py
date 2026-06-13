"""Balance reconciliation simulator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass
from .balance_reconciliation import BalanceSnapshot, BalanceReconResult, reconcile_balance

@dataclass(frozen=True)
class BalanceReconSimulation:
    reconciliation_mode: str
    network_called: bool
    submit_allowed: bool
    results: tuple[BalanceReconResult, ...]
    def to_dict(self) -> dict:
        return {"reconciliation_mode": self.reconciliation_mode, "network_called": self.network_called, "submit_allowed": self.submit_allowed, "results": [r.to_dict() for r in self.results]}

def run_simulation() -> BalanceReconSimulation:
    expected = (
        BalanceSnapshot("USDT", 10000.0, 0.0, 10000.0, True),
        BalanceSnapshot("BTC", 0.5, 0.0, 0.5, True),
        BalanceSnapshot("ETH", 5.0, 0.0, 5.0, True),
    )
    reported = (
        BalanceSnapshot("USDT", 10000.0, 0.0, 10000.0, True),
        BalanceSnapshot("BTC", 0.5, 0.0, 0.5, True),
        BalanceSnapshot("ETH", 5.0, 0.0, 5.0, True),
    )
    reported_map = {r.asset: r for r in reported}
    results = [reconcile_balance(e, reported_map.get(e.asset)) for e in expected]
    return BalanceReconSimulation("SIMULATED_ONLY", False, False, tuple(results))

def run_mismatch_scenario() -> BalanceReconSimulation:
    expected = (
        BalanceSnapshot("USDT", 10000.0, 0.0, 10000.0, True),
        BalanceSnapshot("BTC", 0.5, 0.0, 0.5, True),
    )
    reported = (
        BalanceSnapshot("USDT", 9000.0, 0.0, 9000.0, True),
        BalanceSnapshot("BTC", 0.5, 0.0, 0.5, True),
    )
    reported_map = {r.asset: r for r in reported}
    results = [reconcile_balance(e, reported_map.get(e.asset)) for e in expected]
    return BalanceReconSimulation("SIMULATED_ONLY", False, False, tuple(results))

def write_simulation(sim: BalanceReconSimulation, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sim.to_dict(), indent=2), encoding="utf-8")
