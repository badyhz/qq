"""Integration test: next-stage prerequisite checklist."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_closeout.next_stage_prerequisite_checklist import (
    create_checklist, count_by_status
)


def test_create_checklist():
    checklist = create_checklist()
    assert len(checklist.items) == 10
    assert checklist.next_stage == "READ_ONLY_TESTNET_DISCOVERY"


def test_all_items_not_started():
    checklist = create_checklist()
    for item in checklist.items:
        assert item.status == "NOT_STARTED"


def test_all_items_required():
    checklist = create_checklist()
    required = [i for i in checklist.items if i.required]
    assert len(required) == 10


def test_count_by_status():
    checklist = create_checklist()
    counts = count_by_status(checklist)
    assert counts.get("NOT_STARTED") == 10


def test_render_report():
    from src.runtime_integrations.testnet_mock_closeout.next_stage_prerequisite_checklist import render_report
    checklist = create_checklist()
    report = render_report(checklist)
    assert "NEXT_STAGE_PREREQUISITE_CHECKLIST_READY" in report
    assert "READ_ONLY_TESTNET_DISCOVERY" in report
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in report
