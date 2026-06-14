"""Integration test: readonly stage inventory."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_scope_audit.stage_inventory import create_inventory


def test_create_inventory():
    inventory = create_inventory()
    assert inventory.inventory_id.startswith("SI_")
    assert len(inventory.stages) == 6


def test_all_stages_complete():
    inventory = create_inventory()
    for stage in inventory.stages:
        assert stage.status == "COMPLETE"


def test_stage_ids():
    inventory = create_inventory()
    ids = [s.stage_id for s in inventory.stages]
    for i in range(1, 7):
        assert f"STG_RO_{i:03d}" in ids


def test_all_have_suite_runner():
    inventory = create_inventory()
    for stage in inventory.stages:
        assert stage.suite_runner.endswith("_suite.py")


def test_render_report():
    from src.runtime_integrations.testnet_readonly_scope_audit.stage_inventory import render_report
    inventory = create_inventory()
    report = render_report(inventory)
    assert "READONLY_STAGE_INVENTORY_READY" in report
