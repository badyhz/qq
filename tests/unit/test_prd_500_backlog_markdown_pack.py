"""Tests for prd_500_backlog_markdown_pack — deterministic, no I/O.

T912.
"""

import pytest

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_markdown_pack import (
    Prd500MarkdownPack,
    build_prd_500_markdown_pack,
    markdown_pack_to_dict,
    markdown_pack_to_markdown,
)


# --- Helpers ---


def _make_item(
    task_id: str,
    milestone_id: str = "M1",
    wave_id: str = "W1",
    batch_id: str = "B1",
    risk_level: str = "LOW",
    status: str = "NOT_STARTED",
) -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=task_id,
        title=f"task {task_id}",
        milestone_id=milestone_id,
        wave_id=wave_id,
        batch_id=batch_id,
        risk_level=risk_level,
        status=status,
        dependencies=[],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


def _make_backlog(items) -> PrdBacklog:
    return PrdBacklog(
        backlog_id="test-500-pack",
        items=items,
        total_expected_tasks=len(items),
        status="ACTIVE",
        notes=[],
    )


def _make_500_items() -> list:
    """Build 500 items across 5 milestones."""
    items = []
    for mi in range(1, 6):
        for ti in range(1, 101):
            items.append(
                _make_item(
                    task_id=f"T{mi * 1000 + ti:04d}",
                    milestone_id=f"MS{mi}",
                    wave_id=f"W{mi}",
                    batch_id=f"B{mi}",
                    risk_level="LOW",
                    status="NOT_STARTED",
                )
            )
    return items


# --- Tests ---


class TestMarkdownPack:
    def test_sections_present(self):
        """Pack must have exactly 6 sections."""
        items = _make_500_items()
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        assert len(pack.sections) == 6

    def test_item_count_gte_500(self):
        """Pack item_count must be >= 500 for a 500-item backlog."""
        items = _make_500_items()
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        assert pack.item_count >= 500

    def test_deterministic(self):
        """Same input always produces same output."""
        items = _make_500_items()
        backlog = _make_backlog(items)
        pack1 = build_prd_500_markdown_pack(backlog)
        pack2 = build_prd_500_markdown_pack(backlog)
        d1 = markdown_pack_to_dict(pack1)
        d2 = markdown_pack_to_dict(pack2)
        assert d1 == d2
        md1 = markdown_pack_to_markdown(pack1)
        md2 = markdown_pack_to_markdown(pack2)
        assert md1 == md2

    def test_no_live_authorization(self):
        """Pack must never contain live trading authorization signals."""
        items = _make_500_items()
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        md = markdown_pack_to_markdown(pack)
        forbidden = ["live order", "real order", "execute live", "live trading"]
        for term in forbidden:
            assert term.lower() not in md.lower()

    def test_frozen_blocks_verdict(self):
        """FROZEN items produce BLOCKED verdict."""
        items = [_make_item("T0001", risk_level="FROZEN")]
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        assert pack.final_verdict == "BLOCKED"

    def test_high_warns_verdict(self):
        """HIGH items without FROZEN produce WARN verdict."""
        items = [_make_item("T0001", risk_level="HIGH")]
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        assert pack.final_verdict == "WARN"

    def test_low_passes_verdict(self):
        """Only LOW items produce PASS verdict."""
        items = [_make_item("T0001", risk_level="LOW")]
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        assert pack.final_verdict == "PASS"

    def test_to_dict_keys(self):
        """Dict output has expected keys."""
        items = [_make_item("T0001")]
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        d = markdown_pack_to_dict(pack)
        expected = {"title", "section_count", "item_count", "final_verdict", "notes"}
        assert set(d.keys()) == expected

    def test_to_markdown_contains_header(self):
        """Markdown output contains pack title."""
        items = [_make_item("T0001")]
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        md = markdown_pack_to_markdown(pack)
        assert "test-500-pack" in md

    def test_section_content_non_empty(self):
        """Every section must be non-empty string."""
        items = _make_500_items()
        backlog = _make_backlog(items)
        pack = build_prd_500_markdown_pack(backlog)
        for section in pack.sections:
            assert len(section) > 0
