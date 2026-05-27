"""Tests for PRD Backlog Seed Packet — T880."""

from __future__ import annotations

import pytest

from core.prd_backlog_seed_packet import (
    PrdBacklogSeedPacket,
    backlog_seed_packet_to_dict,
    backlog_seed_packet_to_markdown,
    build_prd_backlog_seed_packet,
)


class TestBuildPrdBacklogSeedPacket:
    def test_default_build(self):
        pkt = build_prd_backlog_seed_packet()
        assert isinstance(pkt, PrdBacklogSeedPacket)
        assert pkt.target_task_count == 500
        assert pkt.backlog_id == "BSEED-001"

    def test_target_task_count_minimum(self):
        with pytest.raises(ValueError, match=">= 500"):
            build_prd_backlog_seed_packet(target_task_count=499)

    def test_target_task_count_500_ok(self):
        pkt = build_prd_backlog_seed_packet(target_task_count=500)
        assert pkt.target_task_count == 500

    def test_target_task_count_1000_ok(self):
        pkt = build_prd_backlog_seed_packet(target_task_count=1000)
        assert pkt.target_task_count == 1000

    def test_live_execution_frozen(self):
        pkt = build_prd_backlog_seed_packet()
        assert any("frozen" in r.lower() for r in pkt.frozen_ranges)
        assert any("M8" in r for r in pkt.frozen_ranges)

    def test_next_safe_range_human_review(self):
        pkt = build_prd_backlog_seed_packet()
        assert "HUMAN_REVIEW_REQUIRED" in pkt.next_safe_range

    def test_deterministic_output(self):
        pkt1 = build_prd_backlog_seed_packet()
        pkt2 = build_prd_backlog_seed_packet()
        assert pkt1 == pkt2
        assert backlog_seed_packet_to_dict(pkt1) == backlog_seed_packet_to_dict(
            pkt2
        )

    def test_frozen_dataclass(self):
        pkt = build_prd_backlog_seed_packet()
        with pytest.raises(AttributeError):
            pkt.target_task_count = 999  # type: ignore[misc]

    def test_milestones_count(self):
        pkt = build_prd_backlog_seed_packet()
        assert len(pkt.proposed_milestones) == 8

    def test_m8_in_milestones(self):
        pkt = build_prd_backlog_seed_packet()
        assert any("M8" in m and "frozen" in m.lower() for m in pkt.proposed_milestones)


class TestBacklogSeedPacketToDict:
    def test_keys(self):
        pkt = build_prd_backlog_seed_packet()
        d = backlog_seed_packet_to_dict(pkt)
        expected_keys = {
            "backlog_id",
            "target_task_count",
            "proposed_milestones",
            "proposed_task_ranges",
            "frozen_ranges",
            "next_safe_range",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_values_match(self):
        pkt = build_prd_backlog_seed_packet()
        d = backlog_seed_packet_to_dict(pkt)
        assert d["target_task_count"] == 500
        assert d["backlog_id"] == "BSEED-001"


class TestBacklogSeedPacketToMarkdown:
    def test_contains_header(self):
        pkt = build_prd_backlog_seed_packet()
        md = backlog_seed_packet_to_markdown(pkt)
        assert "# PRD Backlog Seed Packet" in md

    def test_contains_frozen(self):
        pkt = build_prd_backlog_seed_packet()
        md = backlog_seed_packet_to_markdown(pkt)
        assert "frozen" in md.lower()

    def test_contains_human_review(self):
        pkt = build_prd_backlog_seed_packet()
        md = backlog_seed_packet_to_markdown(pkt)
        assert "HUMAN_REVIEW_REQUIRED" in md
