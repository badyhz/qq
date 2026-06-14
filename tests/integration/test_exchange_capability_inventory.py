"""Integration test: exchange capability inventory."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_discovery.exchange_capability_inventory import (
    create_inventory, count_allowed, count_prohibited
)


def test_create_inventory():
    inventory = create_inventory()
    assert inventory.inventory_id.startswith("INV_")
    assert len(inventory.capabilities) == 10


def test_allowed_count():
    inventory = create_inventory()
    assert count_allowed(inventory) >= 5


def test_prohibited_count():
    inventory = create_inventory()
    assert count_prohibited(inventory) >= 4


def test_submit_prohibited():
    inventory = create_inventory()
    submit_caps = [c for c in inventory.capabilities if "submit" in c.capability_name.lower()]
    for c in submit_caps:
        assert c.allowed_in_current_stage is False
        assert c.final_status == "PROHIBITED"


def test_withdrawal_prohibited():
    inventory = create_inventory()
    withdraw_caps = [c for c in inventory.capabilities if "withdrawal" in c.capability_name.lower()]
    for c in withdraw_caps:
        assert c.allowed_in_current_stage is False


def test_render_report():
    from src.runtime_integrations.testnet_readonly_discovery.exchange_capability_inventory import render_report
    inventory = create_inventory()
    report = render_report(inventory)
    assert "EXCHANGE_CAPABILITY_INVENTORY_READY" in report
    assert "SUBMIT_CAPABILITY_PROHIBITED" in report
