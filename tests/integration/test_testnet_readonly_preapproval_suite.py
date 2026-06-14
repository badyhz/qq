"""Integration test: testnet read-only preapproval suite runner."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_preapproval.approval_packet import create_packet
from src.runtime_integrations.testnet_readonly_preapproval.no_network_preflight_evidence import create_evidence, count_passed
from src.runtime_integrations.testnet_readonly_preapproval.credential_handling_sop import create_sop
from src.runtime_integrations.testnet_readonly_preapproval.operator_checklist import create_checklist
from src.runtime_integrations.testnet_readonly_preapproval.manual_review_queue import create_queue, count_pending
from src.runtime_integrations.testnet_readonly_preapproval.preapproval_safety_regression import run_regression


def test_approval_packet_ready():
    packet = create_packet()
    assert "APPROVAL_PACKET_READY" in packet.final_decision


def test_preflight_evidence_ready():
    evidence = create_evidence()
    assert count_passed(evidence) == len(evidence.items)


def test_credential_sop_ready():
    sop = create_sop()
    assert len(sop.sections) >= 8


def test_operator_checklist_ready():
    checklist = create_checklist()
    assert "HUMAN_APPROVAL_REQUIRED" in checklist.final_decision


def test_manual_review_queue_ready():
    queue = create_queue()
    assert count_pending(queue) == len(queue.items)


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
