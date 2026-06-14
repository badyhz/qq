"""Integration test: network-on blocker drill."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_approval_simulator.network_on_blocker_drill import create_drill


def test_drill_pass():
    drill = create_drill()
    assert "NETWORK_ON_BLOCKER_DRILL_PASS" in drill.final_verdict


def test_all_scenarios_blocked():
    drill = create_drill()
    assert all(s.blocked for s in drill.scenarios)


def test_drill_scenario_count():
    drill = create_drill()
    assert len(drill.scenarios) >= 6
