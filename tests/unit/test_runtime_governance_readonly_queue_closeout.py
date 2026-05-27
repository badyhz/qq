"""Tests for T857 — runtime governance read-only queue closeout."""

import pytest

from core.runtime_governance_readonly_queue_closeout import (
    RuntimeGovernanceReadOnlyQueueCloseout,
    build_readonly_queue_closeout,
    readonly_queue_closeout_to_dict,
    readonly_queue_closeout_to_markdown,
)


@pytest.fixture
def closeout() -> RuntimeGovernanceReadOnlyQueueCloseout:
    return build_readonly_queue_closeout()


class TestDefaults:
    def test_hard_stop_task_is_t857(self, closeout):
        assert closeout.hard_stop_task == "T857"

    def test_next_task_allowed_is_false(self, closeout):
        assert closeout.next_task_allowed is False

    def test_final_message_contains_hard_stop(self, closeout):
        msg = closeout.final_message.lower()
        assert "hard stop" in msg or "do not continue" in msg

    def test_frozen_boundaries_present(self, closeout):
        assert len(closeout.frozen_boundaries) > 0

    def test_queue_range(self, closeout):
        assert closeout.queue_range == "T826-T857"

    def test_completed(self, closeout):
        assert closeout.completed == 32


class TestDeterminism:
    def test_build_is_deterministic(self):
        a = build_readonly_queue_closeout()
        b = build_readonly_queue_closeout()
        assert a == b

    def test_to_dict_is_deterministic(self):
        c = build_readonly_queue_closeout()
        assert readonly_queue_closeout_to_dict(c) == readonly_queue_closeout_to_dict(c)

    def test_to_markdown_is_deterministic(self):
        c = build_readonly_queue_closeout()
        assert readonly_queue_closeout_to_markdown(c) == readonly_queue_closeout_to_markdown(c)


class TestToDict:
    def test_expected_keys(self, closeout):
        d = readonly_queue_closeout_to_dict(closeout)
        expected = {
            "queue_range",
            "completed",
            "hard_stop_task",
            "next_task_allowed",
            "final_message",
            "frozen_boundaries",
        }
        assert set(d.keys()) == expected

    def test_values_match(self, closeout):
        d = readonly_queue_closeout_to_dict(closeout)
        assert d["hard_stop_task"] == "T857"
        assert d["next_task_allowed"] is False


class TestToMarkdown:
    def test_contains_hard_stop(self, closeout):
        md = readonly_queue_closeout_to_markdown(closeout)
        assert "HARD STOP" in md or "Hard stop" in md or "hard stop" in md

    def test_contains_queue_range(self, closeout):
        md = readonly_queue_closeout_to_markdown(closeout)
        assert "T826-T857" in md


class TestFrozen:
    def test_dataclass_is_frozen(self, closeout):
        with pytest.raises(AttributeError):
            closeout.hard_stop_task = "T999"  # type: ignore[misc]
