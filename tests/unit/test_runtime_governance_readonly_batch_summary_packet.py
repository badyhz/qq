"""Tests for T856: Runtime governance read-only batch summary packet."""

from core.runtime_governance_readonly_batch_summary_packet import (
    RuntimeGovernanceReadOnlyBatchSummaryPacket,
    build_readonly_batch_summary_packet,
    readonly_batch_summary_packet_to_dict,
    readonly_batch_summary_packet_to_markdown,
)


def test_task_range():
    pkt = build_readonly_batch_summary_packet()
    assert pkt.task_range == "T826-T856"


def test_total_tasks():
    pkt = build_readonly_batch_summary_packet()
    assert pkt.total_tasks == 31


def test_expected_artifacts():
    pkt = build_readonly_batch_summary_packet()
    assert pkt.expected_artifacts == 93


def test_deterministic():
    a = build_readonly_batch_summary_packet()
    b = build_readonly_batch_summary_packet()
    assert a == b
    assert a is not b


def test_to_dict_has_expected_keys():
    pkt = build_readonly_batch_summary_packet()
    d = readonly_batch_summary_packet_to_dict(pkt)
    expected_keys = {
        "task_range", "total_tasks", "expected_artifacts",
        "final_status", "verification_commands", "notes",
    }
    assert set(d.keys()) == expected_keys


def test_markdown_contains_task_range():
    pkt = build_readonly_batch_summary_packet()
    md = readonly_batch_summary_packet_to_markdown(pkt)
    assert "T826-T856" in md
