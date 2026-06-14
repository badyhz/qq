"""Integration test: testnet read-only release gate suite runner."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_release_gate.release_gate import create_packet
from src.runtime_integrations.testnet_readonly_release_gate.network_off_execution_packet import create_packet as create_exec_packet
from src.runtime_integrations.testnet_readonly_release_gate.credential_air_gap_policy import create_policy
from src.runtime_integrations.testnet_readonly_release_gate.release_blocker_ledger import create_ledger, count_active
from src.runtime_integrations.testnet_readonly_release_gate.operator_signoff_draft import create_draft
from src.runtime_integrations.testnet_readonly_release_gate.release_gate_safety_regression import run_regression


def test_release_gate_packet_ready():
    packet = create_packet()
    assert "READONLY_DISCOVERY_RELEASE_GATE_READY" in packet.final_decision


def test_network_off_packet_ready():
    packet = create_exec_packet()
    assert "NETWORK_OFF_EXECUTION_PACKET_READY" in packet.network_off_verdict


def test_credential_air_gap_ready():
    policy = create_policy()
    assert "CREDENTIAL_AIR_GAP_POLICY_READY" in policy.final_verdict


def test_blocker_ledger_ready():
    ledger = create_ledger()
    assert "READONLY_DISCOVERY_RELEASE_BLOCKERS_READY" in ledger.final_verdict


def test_signoff_draft_ready():
    draft = create_draft()
    assert "READONLY_DISCOVERY_OPERATOR_SIGNOFF_DRAFT_READY" in draft.final_verdict


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
