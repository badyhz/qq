"""Integration test: change control proposal."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_enablement.change_control_proposal import create_proposal
from src.runtime_integrations.testnet_enablement.change_control_validator import validate_proposal


def test_change_control_proposal_created():
    proposal = create_proposal()
    assert proposal.proposal_id.startswith("CCP_")
    assert proposal.scope != ""


def test_change_control_proposal_no_real_submit():
    proposal = create_proposal()
    assert "no real submit" in [ng.lower() for ng in proposal.non_goals]


def test_change_control_proposal_validator_passes():
    proposal = create_proposal()
    checks = validate_proposal(proposal.to_dict())
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_change_control_proposal_has_rollback():
    proposal = create_proposal()
    assert proposal.rollback_plan != ""
    assert proposal.kill_switch_procedure != ""


def test_change_control_proposal_no_submit_allowed():
    proposal = create_proposal()
    d = proposal.to_dict()
    assert d.get("submit_allowed") is not True
