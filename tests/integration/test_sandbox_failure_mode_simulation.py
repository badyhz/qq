"""Test sandbox failure mode simulation."""
import pytest
from src.runtime_integrations.testnet_presubmit.rate_limit_simulator import simulate_rate_limit
from src.runtime_integrations.testnet_presubmit.network_failure_simulator import run_simulation

def test_rate_limit_within_bounds():
    sim = simulate_rate_limit(5, 3)
    assert sim.exceeded is False
    assert sim.no_real_sleep is True

def test_rate_limit_exceeded():
    sim = simulate_rate_limit(2000, 20)
    assert sim.exceeded is True

def test_network_failure_all_handled():
    sim = run_simulation()
    assert sim.all_handled is True
    assert sim.no_real_network is True
    assert len(sim.scenarios) == 7
