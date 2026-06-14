"""Integration test: testnet read-only final governance freeze suite runner."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_governance_freeze.final_governance_freeze import create_freeze
from src.runtime_integrations.testnet_readonly_final_governance_freeze.operator_handoff_packet import create_packet
from src.runtime_integrations.testnet_readonly_final_governance_freeze.no_submit_release_archive import create_archive
from src.runtime_integrations.testnet_readonly_final_governance_freeze.final_governance_safety_regression import run_regression


def test_freeze_ready():
    freeze = create_freeze()
    assert "READONLY_FINAL_GOVERNANCE_FREEZE_READY" in freeze.final_verdict


def test_handoff_ready():
    packet = create_packet()
    assert "READONLY_OPERATOR_HANDOFF_PACKET_READY" in packet.final_verdict


def test_archive_ready():
    archive = create_archive()
    assert "NO_SUBMIT_RELEASE_ARCHIVE_READY" in archive.final_verdict


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
