"""Integration test: read-only discovery operator checklist."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_preapproval.operator_checklist import create_checklist


def test_create_checklist():
    checklist = create_checklist()
    assert checklist.checklist_id.startswith("OPC_")
    assert len(checklist.items) >= 10


def test_all_items_not_started():
    checklist = create_checklist()
    for item in checklist.items:
        assert item.status == "NOT_STARTED"


def test_all_items_required():
    checklist = create_checklist()
    required = [i for i in checklist.items if i.required]
    assert len(required) == len(checklist.items)


def test_has_git_items():
    checklist = create_checklist()
    git_items = [i for i in checklist.items if i.category == "git"]
    assert len(git_items) >= 3


def test_final_decision():
    checklist = create_checklist()
    assert "HUMAN_APPROVAL_REQUIRED" in checklist.final_decision
    assert "REAL_NETWORK_NOT_ALLOWED" in checklist.final_decision


def test_render_report():
    from src.runtime_integrations.testnet_readonly_preapproval.operator_checklist import render_report
    checklist = create_checklist()
    report = render_report(checklist)
    assert "READONLY_DISCOVERY_OPERATOR_CHECKLIST_READY" in report
