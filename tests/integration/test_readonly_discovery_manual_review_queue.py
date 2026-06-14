"""Integration test: read-only discovery manual review queue."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_preapproval.manual_review_queue import (
    create_queue, count_pending
)


def test_create_queue():
    queue = create_queue()
    assert queue.queue_id.startswith("MRQ_")
    assert len(queue.items) >= 5


def test_all_pending():
    queue = create_queue()
    assert count_pending(queue) == len(queue.items)


def test_has_required_types():
    queue = create_queue()
    types = {i.review_type for i in queue.items}
    assert "CREDENTIAL_POLICY_REVIEW" in types
    assert "EXCHANGE_PERMISSION_REVIEW" in types
    assert "GOVERNANCE_REVIEW" in types


def test_decisions():
    queue = create_queue()
    for i in queue.items:
        assert "DO_NOT" in i.final_decision


def test_render_report():
    from src.runtime_integrations.testnet_readonly_preapproval.manual_review_queue import render_report
    queue = create_queue()
    report = render_report(queue)
    assert "READONLY_DISCOVERY_MANUAL_REVIEW_QUEUE_READY" in report
    assert "REAL_NETWORK_NOT_ALLOWED" in report
