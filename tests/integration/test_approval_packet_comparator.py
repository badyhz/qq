"""Integration test: approval packet comparator."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_review.approval_packet_comparator import compare_packets
from src.runtime_integrations.testnet_mock_replay.human_approval_packet_v3 import create_packet


def _make_packet_dict() -> dict:
    return create_packet("BUNDLE_TEST").to_dict()


def test_compare_identical():
    p = _make_packet_dict()
    result = compare_packets(p, p)
    assert result.identical is True
    assert all(not d.changed for d in result.diffs)


def test_compare_different_decision():
    a = _make_packet_dict()
    b = dict(a)
    b["packet_id"] = "MODIFIED"
    b["decision"] = "APPROVAL_PACKET_REVIEWED"
    result = compare_packets(a, b)
    assert result.identical is False
    decision_diff = [d for d in result.diffs if d.field == "decision"]
    assert len(decision_diff) == 1
    assert decision_diff[0].changed is True


def test_compare_different_checklist():
    a = _make_packet_dict()
    b = dict(a)
    b["packet_id"] = "MODIFIED"
    checklists = list(b["checklists"])
    checklists[0] = dict(checklists[0])
    checklists[0]["status"] = "IMPLEMENTED"
    b["checklists"] = checklists
    result = compare_packets(a, b)
    assert len(result.checklist_diffs) >= 1
