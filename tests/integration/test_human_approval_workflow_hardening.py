"""Test human approval workflow hardening."""
import pytest
from src.runtime_integrations.testnet_presubmit.human_approval_workflow import create_hardened_request, validate_hardened_request
from src.runtime_integrations.testnet_presubmit.approval_workflow_validator import validate_workflow_hardening

def test_hardened_request_valid():
    req = create_hardened_request("OP_001", "RV_001", "low risk")
    val = validate_hardened_request(req)
    assert val.valid is True

def test_hardened_request_blocks_submit():
    req = create_hardened_request("OP_001", "RV_001", "low risk")
    val = validate_hardened_request(req)
    assert val.submit_allowed is False
    assert val.approved is False

def test_missing_reviewer_blocks():
    req = create_hardened_request("OP_001", "", "low risk")
    val = validate_hardened_request(req)
    assert val.valid is False

def test_workflow_hardening_passes():
    checks = validate_workflow_hardening()
    assert all(c.passed for c in checks)
