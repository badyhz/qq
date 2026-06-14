"""Integration test: read-only final approval simulator."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_approval_simulator.final_approval_simulator import create_simulation


def test_simulation_ready():
    sim = create_simulation()
    assert "READONLY_FINAL_APPROVAL_SIMULATOR_READY" in sim.final_verdict


def test_simulation_checks_count():
    sim = create_simulation()
    assert len(sim.checks) >= 8


def test_simulation_human_decision_simulated():
    sim = create_simulation()
    assert sim.human_decision == "SIMULATED_PENDING"
