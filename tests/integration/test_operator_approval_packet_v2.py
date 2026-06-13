"""Test operator approval packet v2."""
import pytest
from src.runtime_integrations.testnet_final_gate.operator_approval_packet_v2 import create_packet_v2, validate_packet

def test_packet_valid():
    p = create_packet_v2("OP_001", "RV_001")
    valid, errors = validate_packet(p)
    assert valid is True

def test_packet_has_reviewer():
    p = create_packet_v2("OP_001", "RV_001")
    assert bool(p.reviewer_id) is True

def test_packet_has_no_submit_declaration():
    p = create_packet_v2("OP_001", "RV_001")
    assert bool(p.no_submit_declaration) is True

def test_packet_missing_reviewer_blocks():
    p = create_packet_v2("OP_001", "")
    valid, errors = validate_packet(p)
    assert valid is False
