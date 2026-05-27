"""Tests for T916 — PRD 500 backlog closeout.

Pure deterministic. No I/O. No timestamps. No random.
"""

import pytest

from core.prd_500_backlog_closeout import (
    Prd500BacklogCloseout,
    build_prd_500_backlog_closeout,
    closeout_to_dict,
    closeout_to_markdown,
)


class TestPrd500BacklogCloseout:

    @pytest.fixture(autouse=True)
    def _closeout(self):
        self.closeout = build_prd_500_backlog_closeout()

    def test_item_count_gte_500(self):
        assert self.closeout.materialized_item_count >= 500

    def test_hard_stop_t960(self):
        assert self.closeout.hard_stop == "T960"

    def test_final_status_pass_or_warn(self):
        assert self.closeout.final_status in ("PASS", "WARN", "PARTIAL")
        # If validation passes, final_status matches verdict
        if self.closeout.validation_verdict in ("PASS", "WARN"):
            assert self.closeout.final_status == self.closeout.validation_verdict

    def test_deterministic(self):
        c1 = build_prd_500_backlog_closeout()
        c2 = build_prd_500_backlog_closeout()
        assert c1 == c2

    def test_no_live_authorization(self):
        """No notes or verdicts should contain live trading authorization."""
        forbidden = "authorized for live trading"
        for note in self.closeout.notes:
            assert forbidden not in note.lower()
        assert forbidden not in self.closeout.validation_verdict.lower()
        assert forbidden not in self.closeout.release_hold_verdict.lower()

    def test_task_range_t901_t960(self):
        assert self.closeout.task_range == "T901-T960"

    def test_source_task_count(self):
        assert self.closeout.source_task_count == 16

    def test_closeout_to_dict_keys(self):
        d = closeout_to_dict(self.closeout)
        expected_keys = {
            "task_range",
            "source_task_count",
            "materialized_item_count",
            "milestone_count",
            "wave_count",
            "batch_count",
            "prompt_pack_count",
            "validation_verdict",
            "release_hold_verdict",
            "final_status",
            "hard_stop",
            "next_safe_phase",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_closeout_to_markdown_has_header(self):
        md = closeout_to_markdown(self.closeout)
        assert "PRD 500 Backlog Closeout" in md
        assert "T960" in md
