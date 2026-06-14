"""Integration test: testnet read-only final approval simulator suite runner."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_approval_simulator.final_approval_simulator import create_simulation
from src.runtime_integrations.testnet_readonly_final_approval_simulator.network_on_blocker_drill import create_drill
from src.runtime_integrations.testnet_readonly_final_approval_simulator.human_signoff_archive import create_archive
from src.runtime_integrations.testnet_readonly_final_approval_simulator.final_approval_safety_regression import run_regression


def test_simulation_ready():
    sim = create_simulation()
    assert "READONLY_FINAL_APPROVAL_SIMULATOR_READY" in sim.final_verdict


def test_blocker_drill_pass():
    drill = create_drill()
    assert "NETWORK_ON_BLOCKER_DRILL_PASS" in drill.final_verdict


def test_blocker_drill_expanded():
    drill = create_drill()
    assert len(drill.scenarios) >= 15
    assert "NETWORK_ON_BLOCKER_DRILL_EXPANDED" in drill.final_verdict


def test_signoff_archive_ready():
    archive = create_archive()
    assert "READONLY_HUMAN_SIGNOFF_ARCHIVE_READY" in archive.final_verdict


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
