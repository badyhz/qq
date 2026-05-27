"""Tests for PRD backlog schema — T873."""

import pytest

from core.prd_backlog_schema import (
    PrdBacklog,
    PrdBacklogItem,
    backlog_item_to_dict,
    backlog_item_to_markdown,
    backlog_to_dict,
    backlog_to_markdown,
    build_backlog_item,
    summarize_backlog,
    validate_backlog_item_basic,
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
        "allowed_file_patterns": ["core/*.py"],
        "forbidden_file_patterns": ["*.env"],
        "acceptance_command_ids": ["cmd_001"],
        "notes": [],
    }
    defaults.update(overrides)
    return build_backlog_item(**defaults)


def _make_backlog(items=None, total_expected=500) -> PrdBacklog:
    if items is None:
        items = [_make_item(task_id=f"T{i}", title=f"Task {i}") for i in range(5)]
    return PrdBacklog(
        backlog_id="BL-001",
        items=items,
        total_expected_tasks=total_expected,
        status="NOT_STARTED",
        notes=["test backlog"],
    )


# --- Tests ---


class TestBuildBacklogItem:
    def test_valid_item(self):
        item = _make_item()
        assert item.task_id == "T100"
        assert item.risk_level == "LOW"
        assert item.status == "NOT_STARTED"

    def test_all_risk_levels(self):
        for risk in ("LOW", "MEDIUM", "HIGH", "FROZEN"):
            item = _make_item(risk_level=risk)
            assert item.risk_level == risk

    def test_all_statuses(self):
        for status in ("COMPLETED", "NOT_STARTED", "HUMAN_REVIEW_REQUIRED", "IN_PROGRESS", "BLOCKED", "PARTIAL"):
            item = _make_item(status=status)
            assert item.status == status

    def test_invalid_risk_rejected(self):
        with pytest.raises(ValueError, match="Invalid risk_level"):
            _make_item(risk_level="CRITICAL")

    def test_invalid_status_rejected(self):
        with pytest.raises(ValueError, match="Invalid status"):
            _make_item(status="DONE")

    def test_frozen(self):
        item = _make_item()
        with pytest.raises(AttributeError):
            item.task_id = "T999"  # type: ignore[misc]

    def test_lists_copied(self):
        deps = ["T99"]
        item = _make_item(dependencies=deps)
        deps.append("T100")
        assert item.dependencies == ["T99"]


class TestSerialization:
    def test_item_to_dict_keys(self):
        item = _make_item()
        d = backlog_item_to_dict(item)
        assert set(d.keys()) == {
            "task_id", "title", "milestone_id", "wave_id", "batch_id",
            "risk_level", "status", "dependencies", "allowed_file_patterns",
            "forbidden_file_patterns", "acceptance_command_ids", "notes",
        }

    def test_backlog_to_dict_keys(self):
        bl = _make_backlog()
        d = backlog_to_dict(bl)
        assert set(d.keys()) == {
            "backlog_id", "items", "total_expected_tasks", "status", "notes",
        }
        assert len(d["items"]) == 5

    def test_serializer_deterministic(self):
        item = _make_item()
        d1 = backlog_item_to_dict(item)
        d2 = backlog_item_to_dict(item)
        assert d1 == d2

    def test_backlog_serializer_deterministic(self):
        bl = _make_backlog()
        d1 = backlog_to_dict(bl)
        d2 = backlog_to_dict(bl)
        assert d1 == d2


class TestMarkdown:
    def test_item_markdown_contains_fields(self):
        item = _make_item()
        md = backlog_item_to_markdown(item)
        assert "T100" in md
        assert "M1" in md
        assert "W1" in md
        assert "B1" in md
        assert "LOW" in md
        assert "NOT_STARTED" in md

    def test_item_markdown_deterministic(self):
        item = _make_item()
        assert backlog_item_to_markdown(item) == backlog_item_to_markdown(item)

    def test_backlog_markdown_deterministic(self):
        bl = _make_backlog()
        assert backlog_to_markdown(bl) == backlog_to_markdown(bl)

    def test_backlog_markdown_contains_id(self):
        bl = _make_backlog()
        md = backlog_to_markdown(bl)
        assert "BL-001" in md
        assert "**Expected tasks:** 500" in md


class TestSummary:
    def test_counts_risk_and_status(self):
        items = [
            _make_item(task_id="T1", risk_level="LOW", status="NOT_STARTED"),
            _make_item(task_id="T2", risk_level="LOW", status="COMPLETED"),
            _make_item(task_id="T3", risk_level="HIGH", status="NOT_STARTED"),
        ]
        bl = _make_backlog(items=items)
        s = summarize_backlog(bl)
        assert s["risk_counts"]["LOW"] == 2
        assert s["risk_counts"]["HIGH"] == 1
        assert s["status_counts"]["NOT_STARTED"] == 2
        assert s["status_counts"]["COMPLETED"] == 1
        assert s["actual_items"] == 3

    def test_counts_milestones_and_waves(self):
        items = [
            _make_item(task_id="T1", milestone_id="M1", wave_id="W1"),
            _make_item(task_id="T2", milestone_id="M2", wave_id="W1"),
            _make_item(task_id="T3", milestone_id="M1", wave_id="W2"),
        ]
        bl = _make_backlog(items=items)
        s = summarize_backlog(bl)
        assert s["milestone_counts"]["M1"] == 2
        assert s["milestone_counts"]["M2"] == 1
        assert s["wave_counts"]["W1"] == 2
        assert s["wave_counts"]["W2"] == 1


class TestValidation:
    def test_valid_item_no_issues(self):
        item = _make_item()
        assert validate_backlog_item_basic(item) == []

    def test_empty_task_id(self):
        item = _make_item(task_id="")
        issues = validate_backlog_item_basic(item)
        assert "task_id is empty" in issues

    def test_empty_title(self):
        item = _make_item(title="")
        issues = validate_backlog_item_basic(item)
        assert "title is empty" in issues

    def test_invalid_risk_in_validation(self):
        item = _make_item(risk_level="LOW")
        # bypass build_backlog_item validation to create invalid item
        bad = PrdBacklogItem(
            task_id="T1", title="t", milestone_id="M", wave_id="W",
            batch_id="B", risk_level="BAD", status="NOT_STARTED",
            dependencies=[], allowed_file_patterns=[],
            forbidden_file_patterns=[], acceptance_command_ids=[], notes=[],
        )
        issues = validate_backlog_item_basic(bad)
        assert any("risk_level" in i for i in issues)


class TestBacklog500Plus:
    def test_500_plus_expected(self):
        items = [_make_item(task_id=f"T{i}", title=f"Task {i}") for i in range(10)]
        bl = _make_backlog(items=items, total_expected=600)
        assert bl.total_expected_tasks == 600
        assert len(bl.items) == 10

    def test_500_plus_items_actual(self):
        items = [_make_item(task_id=f"T{i}", title=f"Task {i}") for i in range(510)]
        bl = _make_backlog(items=items, total_expected=510)
        assert len(bl.items) == 510
        s = summarize_backlog(bl)
        assert s["actual_items"] == 510

    def test_backlog_frozen(self):
        bl = _make_backlog()
        with pytest.raises(AttributeError):
            bl.backlog_id = "CHANGED"  # type: ignore[misc]
