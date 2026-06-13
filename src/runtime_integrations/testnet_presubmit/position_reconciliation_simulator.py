"""Position reconciliation simulator. Simulates reconciliation without real API."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass
from .position_reconciliation import PositionSnapshot, ReconciliationResult, reconcile_position

@dataclass(frozen=True)
class PositionReconSimulation:
    reconciliation_mode: str
    network_called: bool
    submit_allowed: bool
    results: tuple[ReconciliationResult, ...]
    def to_dict(self) -> dict:
        return {"reconciliation_mode": self.reconciliation_mode, "network_called": self.network_called, "submit_allowed": self.submit_allowed, "results": [r.to_dict() for r in self.results]}

def run_simulation() -> PositionReconSimulation:
    expected = (
        PositionSnapshot("BTCUSDT", "BUY", 0.001, 50000.0, True),
        PositionSnapshot("ETHUSDT", "SELL", 0.01, 3000.0, True),
        PositionSnapshot("BNBUSDT", "BUY", 0.1, 500.0, True),
    )
    reported = (
        PositionSnapshot("BTCUSDT", "BUY", 0.001, 50000.0, True),
        PositionSnapshot("ETHUSDT", "SELL", 0.01, 3000.0, True),
        PositionSnapshot("BNBUSDT", "BUY", 0.1, 500.0, True),
    )
    reported_map = {r.symbol: r for r in reported}
    results = []
    for e in expected:
        results.append(reconcile_position(e, reported_map.get(e.symbol)))
    return PositionReconSimulation("SIMULATED_ONLY", False, False, tuple(results))

def run_mismatch_scenario() -> PositionReconSimulation:
    expected = (
        PositionSnapshot("BTCUSDT", "BUY", 0.001, 50000.0, True),
        PositionSnapshot("ETHUSDT", "BUY", 0.01, 3000.0, True),
    )
    reported = (
        PositionSnapshot("BTCUSDT", "BUY", 0.002, 50000.0, True),
        PositionSnapshot("ETHUSDT", "SELL", 0.01, 3000.0, True),
    )
    reported_map = {r.symbol: r for r in reported}
    results = []
    for e in expected:
        results.append(reconcile_position(e, reported_map.get(e.symbol)))
    return PositionReconSimulation("SIMULATED_ONLY", False, False, tuple(results))

def write_simulation(sim: PositionReconSimulation, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sim.to_dict(), indent=2), encoding="utf-8")
