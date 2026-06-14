"""Integration test: testnet read-only discovery suite runner."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_discovery.discovery_design import create_design
from src.runtime_integrations.testnet_readonly_discovery.credential_policy_stub import create_policy, validate_policy
from src.runtime_integrations.testnet_readonly_discovery.exchange_capability_inventory import create_inventory, count_prohibited
from src.runtime_integrations.testnet_readonly_discovery.readonly_adapter_contract import create_contract, validate_contract
from src.runtime_integrations.testnet_readonly_discovery.discovery_governance_checklist import create_checklist
from src.runtime_integrations.testnet_readonly_discovery.discovery_dry_run_packet import create_packet
from src.runtime_integrations.testnet_readonly_discovery.readonly_discovery_safety_regression import run_regression


def test_discovery_design_ready():
    design = create_design()
    assert design.final_decision == "READ_ONLY_TESTNET_DISCOVERY_DESIGN_READY"


def test_credential_policy_ready():
    policy = create_policy()
    assert policy.final_decision == "CREDENTIAL_POLICY_STUB_READY"
    assert validate_policy(policy)[0]["valid"] is True


def test_capability_inventory_ready():
    inventory = create_inventory()
    assert count_prohibited(inventory) >= 4


def test_adapter_contract_ready():
    contract = create_contract()
    assert validate_contract(contract)[0]["valid"] is True


def test_governance_checklist_ready():
    checklist = create_checklist()
    assert checklist.final_decision == "DISCOVERY_GOVERNANCE_CHECKLIST_READY"


def test_dry_run_packet_ready():
    packet = create_packet()
    assert "DESIGN_READY" in packet.final_recommendation


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
