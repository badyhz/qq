"""Tests for T848: Runtime governance read-only future task queue."""

import pytest

from core.runtime_governance_readonly_future_task_queue import (
    RuntimeGovernanceReadOnlyFutureTask,
    build_readonly_future_task_queue,
    readonly_future_task_queue_to_dict,
    readonly_future_task_queue_to_markdown,
)


class TestBuildReadonlyFutureTaskQueue:
    def test_returns_exactly_5_tasks(self):
        tasks = build_readonly_future_task_queue()
        assert len(tasks) == 5

    def test_all_blocked_or_queued(self):
        tasks = build_readonly_future_task_queue()
        for t in tasks:
            assert t.status in ("blocked", "queued"), f"{t.task_id} has status {t.status}"

    def test_no_tasks_ready(self):
        tasks = build_readonly_future_task_queue()
        ready = [t for t in tasks if t.status == "ready"]
        assert ready == []

    def test_deterministic(self):
        a = build_readonly_future_task_queue()
        b = build_readonly_future_task_queue()
        assert a == b

    def test_task_ids_unique(self):
        tasks = build_readonly_future_task_queue()
        ids = [t.task_id for t in tasks]
        assert len(ids) == len(set(ids))

    def test_expected_task_ids(self):
        tasks = build_readonly_future_task_queue()
        ids = [t.task_id for t in tasks]
        assert ids == [
            "FUTURE-RO-001",
            "FUTURE-RO-002",
            "FUTURE-RO-003",
            "FUTURE-RO-004",
            "FUTURE-RO-005",
        ]

    def test_frozen_dataclass(self):
        tasks = build_readonly_future_task_queue()
        with pytest.raises(AttributeError):
            tasks[0].task_id = "CHANGED"


class TestReadonlyFutureTaskQueueToDict:
    def test_returns_list_of_dicts(self):
        tasks = build_readonly_future_task_queue()
        result = readonly_future_task_queue_to_dict(tasks)
        assert isinstance(result, list)
        assert len(result) == 5
        for d in result:
            assert isinstance(d, dict)

    def test_dict_keys(self):
        tasks = build_readonly_future_task_queue()
        result = readonly_future_task_queue_to_dict(tasks)
        expected_keys = {"task_id", "title", "risk_level", "status", "dependencies", "notes"}
        for d in result:
            assert set(d.keys()) == expected_keys

    def test_deterministic(self):
        tasks = build_readonly_future_task_queue()
        a = readonly_future_task_queue_to_dict(tasks)
        b = readonly_future_task_queue_to_dict(tasks)
        assert a == b


class TestReadonlyFutureTaskQueueToMarkdown:
    def test_contains_all_task_ids(self):
        tasks = build_readonly_future_task_queue()
        md = readonly_future_task_queue_to_markdown(tasks)
        for t in tasks:
            assert t.task_id in md

    def test_contains_header(self):
        tasks = build_readonly_future_task_queue()
        md = readonly_future_task_queue_to_markdown(tasks)
        assert "Read-Only Future Task Queue" in md

    def test_deterministic(self):
        tasks = build_readonly_future_task_queue()
        a = readonly_future_task_queue_to_markdown(tasks)
        b = readonly_future_task_queue_to_markdown(tasks)
        assert a == b
