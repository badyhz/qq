"""Tests for core.prd_task_model — T865."""

import pytest

from core.prd_task_model import (
    PrdTask,
    PrdTaskRange,
    parse_task_number,
    summarize_task_range,
    task_range_to_dict,
    task_range_to_markdown,
    task_to_dict,
    task_to_markdown,
    validate_task_id,
)


# --- Fixtures ---

def _make_task(**overrides) -> PrdTask:
    defaults = {
        "task_id": "T865",
        "title": "Create PRD task model",
        "status": "IN_PROGRESS",
        "allowed_files": ["core/prd_task_model.py"],
        "dependencies": ["T860"],
        "acceptance_commands": ["python3 -m pytest tests/unit/test_prd_task_model.py"],
        "risk_level": "LOW",
        "notes": ["pure dataclasses"],
    }
    defaults.update(overrides)
    return PrdTask(**defaults)


def _make_range(**overrides) -> PrdTaskRange:
    tasks = overrides.pop("tasks", [_make_task()])
    defaults = {
        "start_task_id": "T865",
        "end_task_id": "T867",
        "tasks": tasks,
        "hard_stop_task_id": "T870",
        "notes": ["sprint 1"],
    }
    defaults.update(overrides)
    return PrdTaskRange(**defaults)


# --- validate_task_id ---


class TestValidateTaskId:
    def test_valid_ids(self):
        assert validate_task_id("T1") is True
        assert validate_task_id("T865") is True
        assert validate_task_id("T0") is True
        assert validate_task_id("T99999") is True

    def test_invalid_ids(self):
        assert validate_task_id("") is False
        assert validate_task_id("t865") is False
        assert validate_task_id("T") is False
        assert validate_task_id("Tabc") is False
        assert validate_task_id("865") is False
        assert validate_task_id("T865a") is False
        assert validate_task_id(" T865") is False

    def test_non_string(self):
        assert validate_task_id(None) is False
        assert validate_task_id(865) is False


# --- parse_task_number ---


class TestParseTaskNumber:
    def test_basic(self):
        assert parse_task_number("T865") == 865
        assert parse_task_number("T1") == 1
        assert parse_task_number("T0") == 0

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_task_number("abc")
        with pytest.raises(ValueError):
            parse_task_number("T")
        with pytest.raises(ValueError):
            parse_task_number("")


# --- Serializers ---


class TestSerializers:
    def test_task_to_dict_keys(self):
        d = task_to_dict(_make_task())
        assert set(d.keys()) == {
            "task_id", "title", "status", "allowed_files",
            "dependencies", "acceptance_commands", "risk_level", "notes",
        }

    def test_task_to_dict_stable(self):
        t = _make_task()
        assert task_to_dict(t) == task_to_dict(t)

    def test_task_to_dict_lists_are_copies(self):
        t = _make_task()
        d = task_to_dict(t)
        d["allowed_files"].append("x")
        assert "x" not in t.allowed_files

    def test_task_range_to_dict_keys(self):
        r = _make_range()
        d = task_range_to_dict(r)
        assert set(d.keys()) == {
            "start_task_id", "end_task_id", "tasks",
            "hard_stop_task_id", "notes",
        }

    def test_task_range_to_dict_nested(self):
        r = _make_range()
        d = task_range_to_dict(r)
        assert len(d["tasks"]) == 1
        assert d["tasks"][0]["task_id"] == "T865"


# --- Markdown ---


class TestMarkdown:
    def test_task_markdown_deterministic(self):
        t = _make_task()
        assert task_to_markdown(t) == task_to_markdown(t)

    def test_task_markdown_contains_id(self):
        t = _make_task()
        md = task_to_markdown(t)
        assert "T865" in md
        assert "Create PRD task model" in md

    def test_range_markdown_deterministic(self):
        r = _make_range()
        assert task_range_to_markdown(r) == task_range_to_markdown(r)

    def test_range_markdown_contains_range(self):
        r = _make_range()
        md = task_range_to_markdown(r)
        assert "T865" in md
        assert "T867" in md
        assert "T870" in md

    def test_task_markdown_no_commands_if_empty(self):
        t = _make_task(acceptance_commands=[])
        md = task_to_markdown(t)
        assert "Acceptance commands" not in md


# --- Summary ---


class TestSummarize:
    def test_total(self):
        r = _make_range(tasks=[_make_task(), _make_task(task_id="T866")])
        s = summarize_task_range(r)
        assert s["total"] == 2

    def test_status_counts(self):
        tasks = [
            _make_task(task_id="T865", status="COMPLETED"),
            _make_task(task_id="T866", status="IN_PROGRESS"),
            _make_task(task_id="T867", status="COMPLETED"),
        ]
        r = _make_range(tasks=tasks)
        s = summarize_task_range(r)
        assert s["status_counts"]["COMPLETED"] == 2
        assert s["status_counts"]["IN_PROGRESS"] == 1

    def test_risk_counts(self):
        tasks = [
            _make_task(task_id="T865", risk_level="HIGH"),
            _make_task(task_id="T866", risk_level="HIGH"),
            _make_task(task_id="T867", risk_level="LOW"),
        ]
        r = _make_range(tasks=tasks)
        s = summarize_task_range(r)
        assert s["risk_counts"]["HIGH"] == 2
        assert s["risk_counts"]["LOW"] == 1

    def test_range_ids_present(self):
        s = summarize_task_range(_make_range())
        assert s["start_task_id"] == "T865"
        assert s["end_task_id"] == "T867"
        assert s["hard_stop_task_id"] == "T870"
