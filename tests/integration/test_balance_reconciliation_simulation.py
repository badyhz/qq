"""Test balance reconciliation simulation."""
import pytest
from src.runtime_integrations.testnet_presubmit.balance_reconciliation_simulator import run_simulation, run_mismatch_scenario

def test_simulation_match():
    sim = run_simulation()
    assert sim.reconciliation_mode == "SIMULATED_ONLY"
    assert sim.network_called is False
    assert sim.submit_allowed is False
    for r in sim.results:
        assert r.status == "MATCH"

def test_mismatch_scenario():
    sim = run_mismatch_scenario()
    blocked = [r for r in sim.results if r.status == "BLOCKED"]
    assert len(blocked) >= 1
