"""Integration test: credential air-gap policy."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_release_gate.credential_air_gap_policy import create_policy


def test_air_gap_policy_ready():
    policy = create_policy()
    assert "CREDENTIAL_AIR_GAP_POLICY_READY" in policy.final_verdict


def test_air_gap_rules_enforced():
    policy = create_policy()
    enforced = [r for r in policy.rules if r.status == "ENFORCED"]
    assert len(enforced) == len(policy.rules)


def test_air_gap_rule_count():
    policy = create_policy()
    assert len(policy.rules) >= 6
