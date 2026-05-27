"""Tests for prd_500_backlog_risk_map — deterministic, no I/O.

T909.
"""

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_risk_map import (
    Prd500RiskMap,
    build_prd_500_risk_map,
    risk_map_to_dict,
    risk_map_to_markdown,
)


# --- Helpers ---


def _make_item(task_id: str, risk_level: str) -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=task_id,
        title=f"task {task_id}",
        milestone_id="M1",
        wave_id="W1",
        batch_id="B1",
        risk_level=risk_level,
        status="NOT_STARTED",
        dependencies=[],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


def _make_backlog(items):
    return PrdBacklog(
        backlog_id="test-backlog",
        items=items,
        total_expected_tasks=len(items),
        status="ACTIVE",
        notes=[],
    )


# --- Tests ---


class TestRiskMap:
    def test_counts_correct(self):
        """Sum of risk counts must equal total_items."""
        items = [
            _make_item("t1", "LOW"),
            _make_item("t2", "LOW"),
            _make_item("t3", "MEDIUM"),
            _make_item("t4", "HIGH"),
            _make_item("t5", "FROZEN"),
            _make_item("t6", "FROZEN"),
        ]
        backlog = _make_backlog(items)
        rm = build_prd_500_risk_map(backlog)
        assert rm.total_items == 6
        assert rm.low_count + rm.medium_count + rm.high_count + rm.frozen_count == rm.total_items

    def test_frozen_triggers_review(self):
        """If frozen > 0, recommended_action includes HUMAN_REVIEW."""
        items = [
            _make_item("t1", "LOW"),
            _make_item("t2", "FROZEN"),
        ]
        backlog = _make_backlog(items)
        rm = build_prd_500_risk_map(backlog)
        assert rm.frozen_count > 0
        assert "HUMAN_REVIEW" in rm.recommended_action

    def test_high_triggers_staged(self):
        """If high > 0 but no frozen, action is STAGED_EXECUTION."""
        items = [
            _make_item("t1", "LOW"),
            _make_item("t2", "HIGH"),
        ]
        backlog = _make_backlog(items)
        rm = build_prd_500_risk_map(backlog)
        assert rm.frozen_count == 0
        assert rm.high_count > 0
        assert "STAGED_EXECUTION" in rm.recommended_action

    def test_low_only_proceeds(self):
        """If only LOW/MEDIUM, action is PROCEED."""
        items = [
            _make_item("t1", "LOW"),
            _make_item("t2", "MEDIUM"),
        ]
        backlog = _make_backlog(items)
        rm = build_prd_500_risk_map(backlog)
        assert "PROCEED" in rm.recommended_action

    def test_human_review_count(self):
        """human_review_required_count == frozen + high."""
        items = [
            _make_item("t1", "HIGH"),
            _make_item("t2", "HIGH"),
            _make_item("t3", "FROZEN"),
            _make_item("t4", "LOW"),
        ]
        backlog = _make_backlog(items)
        rm = build_prd_500_risk_map(backlog)
        assert rm.human_review_required_count == 3

    def test_deterministic(self):
        """Same input always produces same output."""
        items = [
            _make_item("t1", "LOW"),
            _make_item("t2", "HIGH"),
            _make_item("t3", "FROZEN"),
        ]
        backlog = _make_backlog(items)
        rm1 = build_prd_500_risk_map(backlog)
        rm2 = build_prd_500_risk_map(backlog)
        assert risk_map_to_dict(rm1) == risk_map_to_dict(rm2)

    def test_empty_backlog(self):
        """Empty backlog yields zero counts."""
        backlog = _make_backlog([])
        rm = build_prd_500_risk_map(backlog)
        assert rm.total_items == 0
        assert rm.human_review_required_count == 0
        assert "PROCEED" in rm.recommended_action

    def test_to_dict_keys(self):
        """Dict output has expected keys."""
        items = [_make_item("t1", "LOW")]
        backlog = _make_backlog(items)
        rm = build_prd_500_risk_map(backlog)
        d = risk_map_to_dict(rm)
        expected_keys = {
            "total_items",
            "low_count",
            "medium_count",
            "high_count",
            "frozen_count",
            "human_review_required_count",
            "recommended_action",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_to_markdown_contains_header(self):
        """Markdown output contains header."""
        items = [_make_item("t1", "LOW")]
        backlog = _make_backlog(items)
        rm = build_prd_500_risk_map(backlog)
        md = risk_map_to_markdown(rm)
        assert "PRD 500 Backlog Risk Map" in md
