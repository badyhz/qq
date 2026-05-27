"""Tests for PRD 500 backlog dependency map — T908."""

import pytest

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem, build_backlog_item
from core.prd_500_backlog_dependency_map import (
    Prd500DependencyMap,
    build_prd_500_dependency_map,
    dependency_map_to_dict,
    dependency_map_to_markdown,
)


# --- Fixtures ---


def _make_item(**overrides) -> PrdBacklogItem:
    defaults = {
        "task_id": "T100",
        "title": "Test task",
        "milestone_id": "M1",
        "wave_id": "W1",
        "batch_id": "B1",
        "risk_level": "LOW",
        "status": "NOT_STARTED",
        "dependencies": [],
        "allowed_file_patterns": [],
        "forbidden_file_patterns": [],
        "acceptance_command_ids": [],
        "notes": [],
    }
    defaults.update(overrides)
    return build_backlog_item(**defaults)


def _make_backlog(items=None) -> PrdBacklog:
    if items is None:
        items = [_make_item(task_id=f"T{i}", title=f"Task {i}") for i in range(5)]
    return PrdBacklog(
        backlog_id="BL-001",
        items=items,
        total_expected_tasks=500,
        status="NOT_STARTED",
        notes=[],
    )


# --- Tests ---


class TestDependencyMap:
    def test_default_pass_or_warn(self):
        items = [_make_item(task_id=f"T{i}", title=f"Task {i}") for i in range(10)]
        bl = _make_backlog(items=items)
        dm = build_prd_500_dependency_map(bl)
        assert dm.task_count == 10
        assert dm.dependency_count == 0
        assert dm.missing_dependency_count == 0
        assert dm.cycle_count == 0
        assert dm.final_verdict in ("PASS", "WARN")

    def test_missing_dependency_blocked(self):
        items = [
            _make_item(task_id="T1", title="A", dependencies=["T999"]),
            _make_item(task_id="T2", title="B"),
        ]
        bl = _make_backlog(items=items)
        dm = build_prd_500_dependency_map(bl)
        assert dm.missing_dependency_count == 1
        assert dm.final_verdict == "BLOCKED"

    def test_cycle_fail(self):
        items = [
            _make_item(task_id="T1", title="A", dependencies=["T2"]),
            _make_item(task_id="T2", title="B", dependencies=["T1"]),
        ]
        bl = _make_backlog(items=items)
        dm = build_prd_500_dependency_map(bl)
        assert dm.cycle_count >= 1
        assert dm.final_verdict == "FAIL"

    def test_deterministic(self):
        items = [_make_item(task_id=f"T{i}", title=f"Task {i}", dependencies=["T0"] if i > 0 else []) for i in range(5)]
        bl = _make_backlog(items=items)
        dm1 = build_prd_500_dependency_map(bl)
        dm2 = build_prd_500_dependency_map(bl)
        assert dependency_map_to_dict(dm1) == dependency_map_to_dict(dm2)
        assert dependency_map_to_markdown(dm1) == dependency_map_to_markdown(dm2)


class TestDependencyMapFutureDeps:
    def test_future_dep_warn(self):
        items = [
            _make_item(task_id="T01", title="A", dependencies=["T02"]),
            _make_item(task_id="T02", title="B"),
        ]
        bl = _make_backlog(items=items)
        dm = build_prd_500_dependency_map(bl)
        assert dm.future_dependency_count == 1
        assert dm.final_verdict == "WARN"

    def test_valid_backward_dep_pass(self):
        items = [
            _make_item(task_id="T02", title="A", dependencies=["T01"]),
            _make_item(task_id="T01", title="B"),
        ]
        bl = _make_backlog(items=items)
        dm = build_prd_500_dependency_map(bl)
        assert dm.future_dependency_count == 0
        assert dm.dependency_count == 1
        assert dm.final_verdict == "PASS"


class TestDependencyMapSerializers:
    def test_dict_keys(self):
        items = [_make_item(task_id=f"T{i}", title=f"Task {i}") for i in range(3)]
        bl = _make_backlog(items=items)
        dm = build_prd_500_dependency_map(bl)
        d = dependency_map_to_dict(dm)
        assert set(d.keys()) == {
            "task_count",
            "dependency_count",
            "missing_dependency_count",
            "cycle_count",
            "future_dependency_count",
            "final_verdict",
            "notes",
        }

    def test_markdown_contains_verdict(self):
        items = [_make_item(task_id=f"T{i}", title=f"Task {i}") for i in range(3)]
        bl = _make_backlog(items=items)
        dm = build_prd_500_dependency_map(bl)
        md = dependency_map_to_markdown(dm)
        assert "PRD 500 Backlog Dependency Map" in md
        assert dm.final_verdict in md

    def test_frozen(self):
        items = [_make_item(task_id="T1", title="A")]
        bl = _make_backlog(items=items)
        dm = build_prd_500_dependency_map(bl)
        with pytest.raises(AttributeError):
            dm.task_count = 999  # type: ignore[misc]
